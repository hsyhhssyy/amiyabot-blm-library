# 大语言模型库

为其他插件提供大语音模型（ChatGPT，文心一言等）调用库

## 使用方法

### 我是兔兔用户

当你安装了需要该Lib的插件的时候，该插件会因为依赖关系，自动被下载，因此一般情况下你应该不需要手动安装这个插件。

使用时，请在该插件的全局配置项中，填入你的大语言模型相关的密钥和连接。

> 我是ChatGPT用户

> 我是文心一言用户

### 我是兔兔开发者

下面这些函数可以让你调用大语言模型，同时还不必关心模型种类和配置细节。

```python
from core import bot as main_bot

blm_library = main_bot.plugins['amiyabot-blm-library']

if blm_library is not None:
    answer = await blm_library.chat_flow('今天的天气怎么样？')
    ...

```

本插件提供的函数如下：

```python

class BLMFunctionCall:
    functon_name:str
    function_schema:Union[str,dict]
    function:Callable[..., Any]

async def chat_flow(
    prompt: Union[str, list],
	model : Optional[Union[str, dict]],
    context_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    functions: Optional[list[BLMFunctionCall]] = None
    ) -> Optional[str]:
    ...

# 下版本支持
async def assistant_flow(
	assistant: str,
    prompt: Union[str, list],
    context_id: Optional[str] = None
    ) -> Optional[str]:
    ...

# 下版本支持
async def assistant_create(
    name:str,
    instructions:str,
    model: Optional[Union[str, dict]],
    functions: Optional[list[BLMFunctionCall]] = None,
    code_interpreter:bool = false,
    retrieval: Optional[List[str]] = None
    ) -> str:
    ...

def model_list() -> List[dict]:
    ...

def get_model(self,model_name:str) -> dict:
    ...

def get_model_quota_left(self,model_name:str) -> int:
    ...

def get_default_model(self) -> dict:
    ...

async def extract_json(content:str):
    ...

```

#### chat_flow

Chat工作流，以一问一答的形式，与AI进行交互。

参数列表：

| 参数名     | 类型  | 释义   | 默认值 |
|---------|-----|------|-----|
| prompt | Union[str, list] | 要提交给模型的Prompt | 无(不可为空) |
| model |  Union[str,dict] | 选择的模型，既可以是模型的名字，也可以是model_list或get_model返回的dict | None |
| context_id | Optional[str] | 如果你需要保持一个对话，请每次都传递相同的context_id，传递None则表示不保存本次Context。 | None |
| channel_id | Optional[str] | 该次Prompt的ChannelId | None |
| functions | Optional[list[BLMFunctionCall]] | FunctionCall功能，需要模型支持才能生效 | None |

> model可以是字符串，也可以是model_list或get_model返回的dict。在dict的情况下，会访问dict的“model_name”属性来获取模型名称。

> 如果model不存在，会直接返回None。如果传入的model为空，会访问配置项中的‘默认模型’并选择那个模型。

> 关于channel_id，其实本插件并不需要一个channel id，该参数的唯一目的是为了保存token调用量。我建议插件调用时，能传递channel_id的场景尽量传递，无法获取ChannelId的时候也最好传递自己插件的名字等，用于在计费的时候区分。

> functions函数是用于FunctionCall功能，需要模型支持。在model_list中，supported_feature带有"function_call"的模型支持这个功能。目前仅ChatGPT支持该功能，具体的功能说明请看[这个文档](https://platform.openai.com/docs/guides/function-calling)。（下个版本会尝试在文心一言中模拟该功能。）

#### model_list

获取可用的Model的列表。

无参数

返回值为一个字典数组，范例如下：

```python
[
    {"model_name":"gpt-3.5-turbo","type":"low-cost","max-token":2000,"supported_feature":["completion_flow","chat_flow","assistant_flow","function_call"]},
    {"model_name":"gpt-4","type":"high-cost","max-token":4000,"supported_feature":["completion_flow","chat_flow","assistant_flow","function_call"]]},
    {"model_name":"ernie-3.5","type":"low-cost","max-token":4000,"supported_feature":["completion_flow","chat_flow"]},
    {"model_name":"ernie-4","type":"high-cost","max-token":4000,"supported_feature":["completion_flow","chat_flow"]},
]
```

具体返回值会根据用户的配置来确定。如果用户没有配置启动文心一言或者
该函数可以用来配合动态配置文件Schema功能，让其他插件可以在自己的插件配置项中展示并让用户选择Model。
该函数可在函数定义阶段就可用，但是考虑到加载顺序问题，建议不要早于load函数中调用。

返回字典格式说明：

| 参数名     | 类型  | 释义   | 
|---------|-----|------|
| model_name | int | 模型名 | 

**请不要在代码中hardcode模型的名称，在当前版本中，系统会返回诸如ernie-4这样的模型名，但是在未来版本，本插件会支持用户配置两个ChatGPT，三个文心一言这样的设置。届时在返回模型时，就会出现“ERNIE-4(UserDefinedName)”这样的结果。你的HardCode就会失效。**

#### get_model

根据字符串形式的模型名称，返回对应模型的info dict。

#### get_model_quota_left

因为模型的调用配额是可以分开配置的，因此这里可以根据模型名称，查询该模型的配额，开发者可以据此推断模型的行为。

#### get_default_model

前面说过，如果不提供模型，那么会调用用户配置的默认模型，该函数就会返回这个默认模型的info dict，让开发者知道用户配置的默认模型是什么。

#### extract_json

将字符串转为json的帮助函数。使用正则表达式，从一个字符串中提取出一个json数组或者json对象。
和AI其实没什关系，但是是一个很好用的帮助函数。用于处理诸如：

```
好的，输出的json是：
{
    ...
}

```

这样的返回。

### 消耗计算

对于有需要的用户，该Lib会统计每次发送请求时，消耗掉的API Token数量，并且可以分频道计算。
您可以打开amiya_plugin数据库并访问amiyabot-blm-library-token-consume表来查询和统计。

如果您使用收费token，并有分频道计费的需求，可以通过这个数据来实现。

下面给大家一个SQL，可以用来计算花了多少钱，token_cost单位为美元。

```SQL
SELECT
	cast( `consume`.`exec_time` AS date ) AS `exec_date`,
	`consume`.`channel_id` AS `channel_id`,
	`consume`.`model_name` AS `model_name`,
	sum( `consume`.`total_tokens` ) AS `sum(total_tokens)`,
	sum((
		CASE
				
				WHEN ( `consume`.`model_name` = 'gpt-3.5-turbo' ) THEN
				(( `consume`.`total_tokens` * 0.002 ) / 1000 ) 
				WHEN ( `consume`.`model_name` = 'gpt-4' ) THEN
				((( `consume`.`prompt_tokens` * 0.03 ) + ( `consume`.`completion_tokens` * 0.06 )) / 1000 ) ELSE 0 
			END 
			)) AS `token_cost` 
	FROM
		`amiyabot-blm-library-token-consume` `consume` 
	GROUP BY
		`consume`.`model_name`,
		`consume`.`channel_id`,
		cast( `consume`.`exec_time` AS date ) 
	ORDER BY
	`exec_date`,
	`consume`.`channel_id`
```

## 备注

[项目地址:Github](https://github.com/hsyhhssyy/amiyabot-blm-libraryg/)

[遇到问题可以在这里反馈(Github)](https://github.com/hsyhhssyy/amiyabot-blm-library/issues/new/)

## 版本信息

|  版本   | 变更  |
|  ----  | ----  |
| 1.0  | 初版登录商店 |