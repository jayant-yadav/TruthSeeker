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
   
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "developer", 
            "content": f"You are a helpful assistant to a debate moderator and extremely knowledable in debate analysis. Help the moderator by finding rhetorical strategies and fallacies in the arguments provided. \n\
                The debate is on the topic: {topic_of_debate}. \
                Give the quote and their corresponding type of rhetorical strategies used in the following classes: 'Ethos, Pathos, and Logos', 'repetition', 'rhetorical questions', 'hyperbole', 'insults and accusations'.\
                Also provide an argument map in mermaid format, with conculsion, premises, co-premises, objections, counterarguments, rebuttals, inferences and lemmas if only if available in the arument. Do not use prior knowledge."
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
                        },
                        "argument_map": {
                            "type": "string",
                            "description": "A mermaid graph representing the argument map",
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
                    "required": ["rhetorical_strategies", "fallacies", "argument_map"],
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
            return json.loads(llm_response.content)

        except Exception as e:
            print(f"Json parsing error: {e}")
            return None


async def get_fact_check(client, topic_of_debate, gang_violence_debate):
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
                        },
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
            return json.loads(llm_response.content)

        except Exception as e:
            print(f"Json parsing error: {e}")
            return None


async def main():
    # Update the path to the api_keys.json file
    api_keys_path = os.path.join(os.path.dirname(__file__), 'api_keys.json')
    api_keys_file = json.loads(open(api_keys_path).read())
    openapi_key = api_keys_file['openai']
    client = OpenAI(api_key=openapi_key)

    # Make two parallel calls to OpenAI
    task1 = get_rhetorical_analysis(client, topic_of_debate, gang_violence_debate)
    task2 = get_fact_check(client, topic_of_debate, gang_violence_debate)

    results = await asyncio.gather(task1, task2)

    #Just some pretty printing on the console
    console = Console()

    for result in results:
        if result:
            rprint(result)
            if 'rhetorical_strategies' in result and 'fallacies' in result and 'argument_map' in result:
                table = Table(title="Rhetorical Analysis Results")
                table.add_column("Type", justify="left")
                table.add_column("Quote", justify="left")
                table.add_column("Detail", justify="left")

                table.add_row("Rhetorical Strategies", "", "")
                for strategy in result['rhetorical_strategies']:
                    table.add_row("Rhetorical Strategy", strategy['quote'], strategy['strategy'])

                table.add_row("Fallacies", "", "")
                for fallacy in result['fallacies']:
                    table.add_row("Fallacy", fallacy['quote'], fallacy['fallacy'])

                table.add_row("Argument Map", "", result['argument_map'])
                console.print(table)

            elif 'fact_checks' in result:
                table = Table(title="Fact Check Results")
                table.add_column("Quote", justify="left")
                table.add_column("Source", justify="left")
                table.add_column("URL", justify="left")

                table.add_row("Fact Checks", "", "")
                for fact_check in result['fact_checks']:
                    table.add_row(fact_check['quote'], fact_check['source'], fact_check['url'])

                console.print(table)
        else:
            console.print("No response or error occurred.", style="bold red")

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    print("--- %s seconds ---" % (time.time() - start_time))
