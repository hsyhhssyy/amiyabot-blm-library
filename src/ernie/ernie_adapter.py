
import asyncio
from datetime import datetime
import json
import time
from typing import List, Optional, Union

from core import AmiyaBotPluginInstance
from core.util.threadPool import run_in_thread_pool

from amiyabot.log import LoggerManager
from amiyabot.network.httpRequests import http_requests

from ..common.blm_types import BLMAdapter, BLMFunctionCall
from ..common.database import AmiyaBotBLMLibraryMetaStorageModel, AmiyaBotBLMLibraryTokenConsumeModel

logger = LoggerManager('BLM-ERNIE')

class ERNIEAdapter(BLMAdapter):
    def __init__(self, plugin):
        super().__init__()
        self.plugin:AmiyaBotPluginInstance = plugin
        self.context_holder = {}
    
    def debug_log(self, msg):
        show_log = self.plugin.get_config("show_log")
        if show_log == True:
            logger.info(f'{msg}')

    def get_config(self, key, channel_id):
        chatgpt_config = self.plugin.get_config("ERNIE", channel_id)
        if chatgpt_config and chatgpt_config["enable"] and key in chatgpt_config:
            return chatgpt_config[key]
        return None

    async def model_list(self) -> List[dict]:  
        return [
            {"model_name":"ERNIE-Bot","type":"low-cost","supported_feature":["completion_flow","chat_flow"]},
            {"model_name":"ERNIE-Bot-turbo","type":"low-cost","supported_feature":["completion_flow","chat_flow"]},
            {"model_name":"ERNIE-Bot 4.0","type":"hight-cost","supported_feature":["completion_flow","chat_flow"]},
        ]

    async def __get_access_token(self, channel_id):
        appid = self.get_config("app_id", channel_id)

        access_token_key = "ernie_access_token_"+appid

        access_token_meta = AmiyaBotBLMLibraryMetaStorageModel.get_or_none(AmiyaBotBLMLibraryMetaStorageModel.key == access_token_key)
        if access_token_meta is not None:
            self.debug_log(f"app id already exists! Load existing access token")
            try:
                access_token_json = json.loads(access_token_meta.meta_str)
            except Exception as e:
                self.debug_log(f"fail to load access token, error: {e}")
                access_token_json = {}
        else:
            self.debug_log(f"app id first time!")
            access_token_json = {}
        
        if "access_token" in access_token_json and "expire_time" in access_token_json:
            if access_token_json["expire_time"] > time.time():
                return access_token_json["access_token"]
            else:
                self.debug_log(f"access token expired!")
        
        self.debug_log(f"get new access token")

        api_key = self.get_config("api_key", channel_id)
        secret_key = self.get_config("secret_key", channel_id)

        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"

        # post request
        access_token_response_str = await http_requests.post(url, ignore_error=True)

        try:
            access_token_response_json = json.loads(access_token_response_str)
            if "error" in access_token_response_json:
                self.debug_log(f"fail to get access token, error: {access_token_response_json['error']}")
                return None
            else:
                access_token = access_token_response_json["access_token"]
                expire_time = time.time() + access_token_response_json["expires_in"] - 3600 * 24 * 10 # 提前10天
                access_token_meta = AmiyaBotBLMLibraryMetaStorageModel.get_or_none(AmiyaBotBLMLibraryMetaStorageModel.key == access_token_key)
                if access_token_meta:
                    access_token_meta.meta_str = json.dumps({"access_token":access_token,"expire_time":expire_time})
                    access_token_meta.save()
                    self.debug_log(f"update access token: {access_token_meta.meta_str}")
                else:
                    access_token_meta = AmiyaBotBLMLibraryMetaStorageModel(key=access_token_key,meta_str=json.dumps({"access_token":access_token,"expire_time":expire_time}))
                    access_token_meta.save()
                return access_token
        except Exception as e:
            self.debug_log(f"fail to get access token, error: {e}")
            return None

    def __pick_prompt(self, prompts: list, max_chars=4000) -> list:

        text_counter = ""

        for i in range(1, len(prompts) + 1):
            context = prompts[-i]
            text_counter = context["content"] + text_counter
            if len(text_counter) > max_chars:
                return prompts[-i + 1 :]
        
        return prompts

    async def chat_flow(  
        self,  
        prompt: Union[str, List[str]],  
        model: str,
        context_id: Optional[str] = None,  
        channel_id: Optional[str] = None,
        functions: Optional[List[BLMFunctionCall]] = None,  
        ) -> Optional[str]:
        
        access_token = await self.__get_access_token(channel_id)

        if not access_token:
            return None

        if isinstance(prompt, str):
            prompt = [prompt]
        
        # 百度对Message的要求比较奇葩
        # 必须为奇数个成员，成员中message的role必须依次为user、assistant
        # 所以用户的提交必须合并

        big_prompt = "\n".join(prompt)

        prompt = [{"role": "user", "content": big_prompt}]

        if context_id is not None:
            if context_id not in self.context_holder:
                self.context_holder[context_id] = []
            prompt = self.context_holder[context_id] + prompt
        
        # 以防万一，进行一个检查，如果prompt列表不是 user 和 assistant 交替出现，
        # 那么就从集合抽出有问题的项目并报日志

        expected_roles = ['user', 'assistant']

        # 当列表中至少有两个元素时循环检查
        while len(prompt) > 1:
            # 检查列表中的每个元素
            for i in range(len(prompt) - 1):
                # 如果当前元素和下一个元素的角色相同或者不符合期望的顺序
                if prompt[i]['role'] == prompt[i + 1]['role'] or prompt[i]['role'] != expected_roles[i % 2]:
                    self.debug_log(f"prompt list order error, remove prompt: {prompt[i]}")
                    del prompt[i]
                    break
            else:
                # 如果所有元素都符合条件，则退出循环
                break

        # 百度的API不需要检测字数，但是为了减少网络流量，这里限制到4000个字。
        # 从后向前计算content的累计字数，砍掉超过4000字的部分，直到字数小于4000

        prompt = self.__pick_prompt(prompt, 4000)

        if len(prompt) % 2 != 1:
            self.debug_log(f"prompt list is not odd, prompt: {prompt}")
            # 移除第一个元素，使其变为奇数
            del prompt[0]
        
        # Post调用

        model_url_map = {
            "ERNIE-Bot 4.0":"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro",
            "ERNIE-Bot":"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions",
            "ERNIE-Bot-turbo":"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/eb-instant"
        }

        if model not in model_url_map:
            self.debug_log(f"model {model} not supported")
            return None
        
        url = model_url_map[model] + "?access_token=" + access_token

        headers = {
            "Content-Type":"application/json"
        }

        data = {
            "messages":[
                {
                    "role":prompt[i]["role"],
                    "content":prompt[i]["content"]
                } for i in range(len(prompt))            
            ]
        }

        response_str = await http_requests.post(url, headers=headers, payload=data, ignore_error=True)

        try:
            response_json = json.loads(response_str)

            if "error_code" in response_json:
                self.debug_log(f"fail to chat, error: {response_json['error_msg']} \n {response_str}")
                return None

            # 校验和取值

            result = response_json["result"]
            usage = response_json["usage"]
            id = response_json["id"]
            _ = usage["prompt_tokens"]
            _ = usage["completion_tokens"]
            _ = usage["total_tokens"]
        except Exception as e:
            self.debug_log(f"fail to chat, error: {e} \n {response_str}")
            return None
        
        combined_message = '\n'.join(obj['content'] for obj in prompt)

        self.debug_log(f'ERNIE Raw: \n{combined_message}\n------------------------\n{result}')

        # 出于调试目的，写入请求数据
        formatted_file_timestamp = time.strftime('%Y%m%d', time.localtime(time.time()))
        sent_file = f'{self.cache_dir}/ERNIE.{channel_id}.{formatted_file_timestamp}.txt'
        with open(sent_file, 'a', encoding='utf-8') as file:
            file.write('-'*20)
            formatted_timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            file.write(f'{formatted_timestamp}')
            file.write('-'*20)
            file.write('\n')
            file.write(f'{combined_message}')
            file.write('\n')
            file.write('-'*20)
            file.write('\n')
            file.write(f'{result}')
            file.write('\n')

        AmiyaBotBLMLibraryTokenConsumeModel.create(
            channel_id=channel_id, model_name=model, exec_id=id,
            prompt_tokens=int(usage['prompt_tokens']),
            completion_tokens=int(usage['completion_tokens']),
            total_tokens=int(usage['total_tokens']), exec_time=datetime.now())
        
        if context_id is not None:
            prompt.append({"role": "assistant", "content": result})
            self.context_holder[context_id] = prompt

        return f"{result}".strip()