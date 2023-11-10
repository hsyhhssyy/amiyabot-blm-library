import os
import re

from amiyabot import Message, Chain, log

from .src.common.blm_plugin_instance import BLMLibraryPluginInstance

curr_dir = os.path.dirname(__file__)
                
bot = BLMLibraryPluginInstance(
    name='大语言模型调用库',
    version='1.0',
    plugin_id='amiyabot-blm-library',
    plugin_type='',
    description='为其他插件提供大语音模型调用库',
    document=f'{curr_dir}/README.md',
    global_config_default=f'{curr_dir}/config_templates/global_config_default.json',
    global_config_schema=f'{curr_dir}/config_templates/global_config_schema.json', 
)

@bot.on_message(keywords=['测试调用库'], level=5)
async def test_call_lib(data: Message):
    ret = await bot.chat_flow('测试调用库', 'ERNIE-Bot')
    log.info(ret)
    return Chain(data).text(ret)