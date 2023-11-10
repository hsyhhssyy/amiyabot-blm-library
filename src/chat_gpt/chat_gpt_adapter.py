
import time
import openai

from datetime import datetime

from typing import List, Optional, Union

from core import AmiyaBotPluginInstance
from core.util.threadPool import run_in_thread_pool

from amiyabot.log import LoggerManager

from ..common.database import AmiyaBotBLMLibraryTokenConsumeModel
from ..common.blm_types import BLMAdapter, BLMFunctionCall

logger = LoggerManager('BLM-ChatGPT')

class ChatGPTAdapter(BLMAdapter):
    def __init__(self, plugin):
        super().__init__()
        self.plugin:AmiyaBotPluginInstance = plugin
        self.context_holder = {}

    def debug_log(self, msg):
        show_log = self.plugin.get_config("show_log")
        if show_log == True:
            logger.info(f'{msg}')

    def get_config(self, key, channel_id):
        chatgpt_config = self.plugin.get_config("ChatGPT", channel_id)
        if chatgpt_config and chatgpt_config["enable"] and key in chatgpt_config:
            return chatgpt_config[key]
        return None
        

    async def model_list(self) -> List[dict]:  
        return [
            {"model_name":"gpt-3.5-turbo","type":"low-cost","supported_flow":["completion_flow","chat_flow","assistant_flow"]},
            {"model_name":"gpt-4","type":"hight-cost","supported_flow":["completion_flow","chat_flow","assistant_flow"]},
        ]
    
    async def chat_flow(  
        self,  
        prompt: Union[str, List[str]],  
        model: str,
        context_id: Optional[str] = None,  
        channel_id: Optional[str] = None,
        functions: Optional[List[BLMFunctionCall]] = None,  
    ) -> Optional[str]:  
        
        openai.api_key = self.get_config('api_key', channel_id)

        proxy = self.get_config('proxy', channel_id)
        if proxy:
            self.debug_log(f"proxy set: {proxy}")
            openai.proxy = proxy

        if model is None:
            model = "gpt-3.5-turbo"

        base_url = self.get_config('url', channel_id)
        if base_url:
            openai.api_base = base_url

        response = None

        self.debug_log(f"url: {base_url} proxy: {proxy} model: {model}")
        

        if isinstance(prompt, str):
            prompt = [prompt]
        
        if context_id is not None:
            if context_id not in self.context_holder:
                self.context_holder[context_id] = []
            prompt = self.context_holder[context_id] + prompt

        prompt = [{"role": "user", "content": command} for command in prompt]
        
        combined_message = ''.join(obj['content'] for obj in prompt)

        try:
            response = await run_in_thread_pool(
                openai.ChatCompletion.create,
                **{'model': model, 'messages': prompt}
            )
            
        except openai.error.RateLimitError as e:
            self.debug_log(f"RateLimitError: {e}")
            self.debug_log(f'Chatgpt Raw: \n{combined_message}')
            return None
        except openai.error.InvalidRequestError as e:
            self.debug_log(f"InvalidRequestError: {e}")
            self.debug_log(f'Chatgpt Raw: \n{combined_message}')
            return None
        except Exception as e:
            self.debug_log(f"Exception: {e}")
            self.debug_log(f'Chatgpt Raw: \n{combined_message}')
            return None

        text: str = response['choices'][0]['message']['content']
        # role: str = response['choices'][0]['message']['role']
        
        self.debug_log(f'Chatgpt Raw: \n{combined_message}\n------------------------\n{text}')

         # 出于调试目的，写入请求数据
        formatted_file_timestamp = time.strftime('%Y%m%d', time.localtime(time.time()))
        sent_file = f'{self.cache_dir}/{channel_id}.{formatted_file_timestamp}.txt'
        with open(sent_file, 'a', encoding='utf-8') as file:
            file.write('-'*20)
            formatted_timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            file.write(f'{formatted_timestamp}')
            file.write('-'*20)
            file.write('\n')
            all_contents = "\n".join([item["content"] for item in prompt])
            file.write(f'{all_contents}')
            file.write('\n')
            file.write('-'*20)
            file.write('\n')
            file.write(f'{text}')
            file.write('\n')

        id = response['id']
        usage = response['usage']

        if channel_id is None:
            channel_id = "-"

        if model is None:
            model = "-"

        AmiyaBotBLMLibraryTokenConsumeModel.create(
            plugin_id="-",json_config="-",version="-",
            channel_id=channel_id, model_name=model, exec_id=id,
            prompt_tokens=int(usage['prompt_tokens']),
            completion_tokens=int(usage['completion_tokens']),
            total_tokens=int(usage['total_tokens']), exec_time=datetime.now())

        if context_id is not None:
            prompt.append({"role": "assistant", "content": text})
            self.context_holder[context_id] = prompt

        return f"{text}".strip()