from openai import OpenAI
import os
import asyncio
import json
from debates import topic_of_debate, gang_violence_debate
from rich.pretty import pprint as rprint
import time
from rich.table import Table
from rich.console import Console

async def get_rhetorical_analysis(client, topic_of_debate, gang_violence_debate):
    start_time = time.time()
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "developer", 
            "content": f"You are a helpful assistant to a debate moderator and extremely knowledable in debate analysis. Help the moderator by finding rhetorical strategies and fallacies in the arguments provided. \n\
                The debate is on the topic: {topic_of_debate}. \
                Give the quote and their corresponding type of rhetorical strategies used in the following classes: 'Ethos, Pathos, and Logos', 'repetition', 'rhetorical questions', 'hyperbole', 'insults and accusations'."
            },
            
            {
                "role": "user",
                "content": f"{gang_violence_debate}"
            }
        ],
        response_format={
            "type": "json_schema", 
            "json_schema": {
                "name": "moderation_help",
                "strict": True,
                "schema":{
                    "type": "object",
                    "properties": {
                        "rhetorical_strategies": {
                            "type": "array",
                            "description": "Rhetorical stategies in the argument",
                            "items": {"$ref": "#/$defs/rhetorical_strategy"}
                        },
                        "fallacies": {
                            "type": "array",
                            "description": "Fallacies in the argument",
                            "items": {"$ref": "#/$defs/fallacy"}
                        }                        
                    },
                    "$defs": {
                        "rhetorical_strategy": {
                            "type": "object",
                            "description": "Quote and its corresponding rhetorical stategy",
                            "properties": {
                                "quote": {
                                    "type": "string",
                                    "description": "The quote from the argument",
                                },
                                "strategy": {
                                    "type": "string",
                                    "description": "The rhetorical strategy in the quote",
                                }
                            },
                            "required": ["quote", "strategy"],
                            "additionalProperties": False
                        },
                        "fallacy": {
                            "type": "object",
                            "description": "Quote and its corresponding fallacy",
                            "properties": {
                                "quote": {
                                    "type": "string",
                                    "description": "The quote from the argument",
                                },
                                "fallacy": {
                                    "type": "string",
                                    "description": "The fallacy in the quote",
                                }
                            },
                            "required": ["quote", "fallacy"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["rhetorical_strategies", "fallacies"],
                    "additionalProperties": False
                } 
            }
        }
    )

    llm_response = completion.choices[0].message

    if llm_response.refusal:
        print(llm_response.refusal)
        return None
    else:
        try: 
            print("--- Rhetoric analysis reponse in  %s seconds ---" % (time.time() - start_time))
            return json.loads(llm_response.content)

        except Exception as e:
            print(f"Json parsing error: {e}")
            return {"error": "json_parsing_error"}


async def get_fact_check(client, topic_of_debate, gang_violence_debate):
    start_time = time.time()
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "developer", 
             "content": f"You are a helpful assistant to a debate moderator and extremely knowledable in debate analysis. Help the moderator by checking for facts in the arguments provided. \n\
                The debate is on the topic: {topic_of_debate}. \
                Give the quote and its corresponding sources from where it can be fact checked. The sources should be research papers, news channels and journal articles."
            },
             
            {
                "role": "user",
                "content": f"{gang_violence_debate}"
            }
        ],
        response_format={
            "type": "json_schema", 
            "json_schema": {
                "name": "moderation_help",
                "strict": True,
                "schema":{
                    "type": "object",
                    "properties": {
                        "fact_checks": {
                            "type": "array",
                            "description": "Facts sources for quotes in the argument",
                            "items": {"$ref": "#/$defs/fact_check"}
                        }  
                    },
                    "$defs": {
                        "fact_check": {
                            "type": "object",
                            "description": "Quote and its corresponding fact check source",
                            "properties": {
                                "quote": {
                                    "type": "string",
                                    "description": "The quote from the argument",
                                },
                                "source": {
                                    "type": "string",
                                    "description": "The source from where the quote can be fact checked",
                                },
                                "url": {
                                    "type": "string",
                                    "description": "The url of the source",
                                }
                            },
                            "required": ["quote", "source", "url"],
                            "additionalProperties": False
                        }
                    },
                    "required": ["fact_checks"],
                    "additionalProperties": False
                } 
            }
        }
    )

    llm_response = completion.choices[0].message

    if llm_response.refusal:
        print(llm_response.refusal)
        return None
    else:
        try: 
            print("--- Fact-checker reponse in  %s seconds ---" % (time.time() - start_time))
            return json.loads(llm_response.content)

        except Exception as e:
            print(f"Json parsing error: {e}")
            return {"error": "json_parsing_error"}

async def get_argument_map(client, topic_of_debate, gang_violence_debate):
    start_time = time.time()
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "developer", 
            "content": f"You are a helpful assistant to a debate moderator and extremely knowledable in debate analysis. Help the moderator by providing an argument map in mermaid format, with conculsion, premises, co-premises, objections, counterarguments, rebuttals, inferences and lemmas if only if available in the arument. \n\
                The debate is on the topic: {topic_of_debate}."
            },
            
            {
                "role": "user",
                "content": f"{gang_violence_debate}"
            }
        ],
        response_format={
            "type": "json_schema", 
            "json_schema": {
                "name": "moderation_help",
                "strict": True,
                "schema":{
                    "type": "object",
                    "properties": {
                        
                        "argument_map": {
                            "type": "string",
                            "description": "A mermaid graph representing the argument map",
                        }
                    },
                    "required": ["argument_map"],
                    "additionalProperties": False
                } 
            }
        }
    )

    llm_response = completion.choices[0].message

    if llm_response.refusal:
        print(llm_response.refusal)
        return None
    else:
        try: 
            print("--- Argument map reponse in  %s seconds ---" % (time.time() - start_time))
            return json.loads(llm_response.content)

        except Exception as e:
            print(f"Json parsing error: {e}")
            return {"error": "json_parsing_error"}


async def main():
    # Update the path to the api_keys.json file
    api_keys_path = os.path.join(os.path.dirname(__file__), 'api_keys.json')
    api_keys_file = json.loads(open(api_keys_path).read())
    openapi_key = api_keys_file['openai']
    client = OpenAI(api_key=openapi_key)

    # Make two parallel calls to OpenAI
    task1 = get_rhetorical_analysis(client, topic_of_debate, gang_violence_debate)
    task2 = get_fact_check(client, topic_of_debate, gang_violence_debate)

    # Task3 is for post analysis of debate
    # task3 = get_argument_map(client, topic_of_debate, gang_violence_debate)
    # results = await asyncio.gather(task1, task2, task3)

    start_time = time.time()
    results = await asyncio.gather(task1, task2)
    print("--- Gather response in %s seconds ---" % (time.time() - start_time))


    for result in results:
        if result and not result.get("error"):
            rprint(result)

        elif result.get("error"):
            
            rprint("error occurred, retring...")
            task1 = get_rhetorical_analysis(client, topic_of_debate, gang_violence_debate)
            task2 = get_fact_check(client, topic_of_debate, gang_violence_debate)
            results = await asyncio.gather(task1, task2)
            for result in results:
                if result and not result.get("error"):
                    rprint(result)
                elif result.get("error"):
                    rprint("error occurred again. Giving up!")
                else:
                    rprint("No response or error occurred.")

        else:
            rprint("No response or error occurred.")

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    print("--- Overall reponse in %s seconds ---" % (time.time() - start_time))
