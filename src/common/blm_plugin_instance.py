import asyncio
import json
from typing import Any, Dict, List, Optional, Union

from core import AmiyaBotPluginInstance,Requirement
from core.plugins.customPluginInstance.amiyaBotPluginInstance import CONFIG_TYPE,DYNAMIC_CONFIG_TYPE

from ..common.blm_types import BLMAdapter, BLMFunctionCall
from ..chat_gpt.chat_gpt_adapter import ChatGPTAdapter 
from ..ernie.ernie_adapter import ERNIEAdapter 
from ..common.database import AmiyaBotBLMLibraryTokenConsumeModel,AmiyaBotBLMLibraryMetaStorageModel

class BLMLibraryPluginInstance(AmiyaBotPluginInstance,BLMAdapter):
    def __init__(self, name: str, 
                 version: str, 
                 plugin_id: str, 
                 plugin_type: str = None, 
                 description: str = None, 
                 document: str = None, 
                 priority: int = 1, 
                 instruction: str = None, 
                 requirements: Union[List[Requirement],None] = None,
                 channel_config_default: CONFIG_TYPE = None,
                 channel_config_schema: DYNAMIC_CONFIG_TYPE = None, 
                 global_config_default: CONFIG_TYPE = None, 
                 global_config_schema: DYNAMIC_CONFIG_TYPE = None, 
                 deprecated_config_delete_days: int = 7):
        super().__init__(name, version, plugin_id, plugin_type, description, document, priority, instruction, requirements, channel_config_default, channel_config_schema, global_config_default, global_config_schema, deprecated_config_delete_days)
        self.adapters: List[BLMAdapter] = []
        self.model_map: Dict[str,BLMAdapter] = {}

    def install(self):
        
        AmiyaBotBLMLibraryTokenConsumeModel.create_table(safe=True)
        AmiyaBotBLMLibraryMetaStorageModel.create_table(safe=True)

        # 读取配置文件来确定各个模型是不是启用
        chatgpt_config = self.get_config("ChatGPT")
        if chatgpt_config and chatgpt_config["enable"]:
            self.adapters.append(ChatGPTAdapter(self))
        ernie_config = self.get_config("ERNIE")
        if ernie_config and ernie_config["enable"]:
            self.adapters.append(ERNIEAdapter(self))
        
        # Schedule the coroutine to run in the existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(self.model_list())
        else:
            loop.run_until_complete(self.model_list())

    async def model_list(self) -> List[dict]:  
        # 返回的同时，构造ModelMap，方便后续的模型调用
        model_list = []
        for adapter in self.adapters:
            adapter_models = await adapter.model_list()
            model_list.extend(adapter_models)
            for model in adapter_models:
                self.model_map[model["model_name"]] = adapter
        return model_list
    
    # 以下是对外提供的接口, 通过model_name来确定调用哪个模型

    async def completion_flow(  
        self,  
        prompt: Union[str, List[str]],  
        model: str,
        context_id: Optional[str] = None,
        channel_id: Optional[str] = None,
    ) -> Optional[str]:  
        adapter = self.model_map[model]
        if not adapter:
            return None
        return await adapter.completion_flow(prompt, model, context_id, channel_id)

    async def chat_flow(  
        self,  
        prompt: Union[str, List[str]],  
        model: str,
        context_id: Optional[str] = None,  
        channel_id: Optional[str] = None,
        functions: Optional[List[BLMFunctionCall]] = None,  
    ) -> Optional[str]:  
        adapter = self.model_map[model]
        if not adapter:
            return None
        return await adapter.chat_flow(prompt, model, context_id, channel_id, functions)

    async def assistant_flow(  
        self,  
        assistant: str,  
        prompt: Union[str, List[str]],  
        context_id: Optional[str] = None,        
        channel_id: Optional[str] = None,
    ) -> Optional[str]:
        adapter = self.model_map[assistant]
        if not adapter:
            return None
        return await adapter.assistant_flow(assistant, prompt, context_id, channel_id)
    
    async def assistant_create(  
        self,  
        name: str,  
        instructions: str,  
        model: str ,
        functions: Optional[List[BLMFunctionCall]] = None,  
        code_interpreter: bool = False,  
        retrieval: Optional[List[str]] = None,  
    ) -> str:
        adapter = self.model_map[model]
        if not adapter:
            return None
        return await adapter.assistant_create(name, instructions, model, functions, code_interpreter, retrieval)
    
    def extract_json(self, string: str) -> List[Union[Dict[str, Any], List[Any]]]:
        json_strings = []
        json_objects = []
        
        # We need additional variables to handle arrays
        open_curly_brackets = 0
        open_square_brackets = 0
        start_index = None

        for index, char in enumerate(string):
            if char == '{':
                open_curly_brackets += 1
            elif char == '}':
                open_curly_brackets -= 1
            elif char == '[':
                open_square_brackets += 1
            elif char == ']':
                open_square_brackets -= 1
            else:
                continue

            # Check when to start capturing the string
            if (open_curly_brackets == 1 and open_square_brackets == 0 and start_index is None) or \
            (open_square_brackets == 1 and open_curly_brackets == 0 and start_index is None):
                start_index = index

            # Check when to stop capturing the string
            if (open_curly_brackets == 0 and open_square_brackets == 0 and start_index is not None):
                json_strings.append(string[start_index : index + 1])
                start_index = None

        for json_str in json_strings:
            try:
                json_object = json.loads(json_str)
                json_objects.append(json_object)
            except json.JSONDecodeError as e:
                pass

        return json_objects