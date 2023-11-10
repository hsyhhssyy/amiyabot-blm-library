
import asyncio
import json
import time
from typing import List, Optional, Union

from core import AmiyaBotPluginInstance
from core.util.threadPool import run_in_thread_pool

from amiyabot.log import LoggerManager

from ..common.blm_types import BLMAdapter, BLMFunctionCall
from ..common.database import AmiyaBotBLMLibraryMetaStorageModel

logger = LoggerManager('BLM-ERNIE')

class ERNIEAdapter(BLMAdapter):
    def __init__(self, plugin):
        super().__init__()
        self.plugin:AmiyaBotPluginInstance = plugin
    
    def debug_log(self, msg):
        show_log = self.plugin.get_config("show_log")
        if show_log == True:
            logger.info(f'{msg}')

    def get_config(self, key):
        chatgpt_config = self.get_config("ERNIE")
        if chatgpt_config and chatgpt_config["enable"] and key in chatgpt_config:
            return chatgpt_config[key]
        return None

    async def model_list(self) -> List[dict]:  
        return [
            {"model_name":"ernie-3.5","type":"low-cost","supported_flow":["completion_flow","chat_flow"]},
            {"model_name":"ernie-4","type":"hight-cost","supported_flow":["completion_flow","chat_flow"]},
        ]

    async def __get_access_token(self):
        appid = self.get_config("app_id")
        access_token_meta = AmiyaBotBLMLibraryMetaStorageModel.select(AmiyaBotBLMLibraryMetaStorageModel.key == "ernie_access_token_"+appid).first()
        if access_token_meta:
            access_token_json = json.loads(access_token_meta.meta_str)
        else:
            access_token_json = {}
        
        if "access_token" in access_token_json and "expire_time" in access_token_json:
            if access_token_json["expire_time"] > time.time():
                return access_token_json["access_token"]
        
        app_key = self.get_config("app_key")
        secret_key = self.get_config("secret_key")

        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={app_key}&client_secret={secret_key}"

    async def chat_flow(  
        self,  
        prompt: Union[str, List[str]],  
        model: str,
        context_id: Optional[str] = None,  
        channel_id: Optional[str] = None,
        functions: Optional[List[BLMFunctionCall]] = None,  
        ) -> Optional[str]:
        ...