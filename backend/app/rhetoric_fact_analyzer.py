import time
import json
from openai import OpenAI
import asyncio
import logging
from typing import List, Dict, Any
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)


class FactCheck(BaseModel):
    quote: str
    source: str
    url: str

class RhetoricalStrategy(BaseModel):
    quote: str
    strategy: str

class Fallacy(BaseModel):
    quote: str
    fallacy: str

class RhetoricAnalysis(BaseModel):
    rhetorical_strategies: List[RhetoricalStrategy]
    fallacies: List[Fallacy]

class RhetoricFactAnalysis(BaseModel):
    rhetorical_analysis: RhetoricAnalysis
    fact_checks: List[FactCheck]

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
        logger.info(f"LLM refused to provide response : {llm_response.refusal}")
        return None
    else:
        try: 
            logger.info("--- Rhetoric analysis reponse in  %s seconds ---" % (time.time() - start_time))
            return json.loads(llm_response.content)

        except Exception as e:
            logger.info(f"Json parsing error: {e}")
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
        logger.info(f"LLM refused to provide response : {llm_response.refusal}")
        return None
    else:
        try: 
            logger.info("--- Fact-checker reponse in  %s seconds ---" % (time.time() - start_time))
            return json.loads(llm_response.content)

        except Exception as e:
            logger.info(f"Json parsing error: {e}")
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
        logger.info(f"LLM refused to provide response : {llm_response.refusal}")
        return None
    else:
        try: 
            logger.info("--- Argument map reponse in  %s seconds ---" % (time.time() - start_time))
            return json.loads(llm_response.content)

        except Exception as e:
            logger.info(f"Json parsing error: {e}")
            return {"error": "json_parsing_error"}

topic_of_debate = "Escalation of gang violence in Sweden and strengthening the fight against organised crime"
gang_violence_debate = f"President. – The next item on the agenda is the debate on the Commission statement on the escalation of gang violence in Sweden and strengthening the fight against organised crime\n\n Maria Luís Albuquerque, Member of the Commission. – Madam President, honourable Members, the horrendous attack in Örebro – one of the worst attacks in Swedish history – has shocked as all to the core. And I would like to express my heartfelt condolences to the families and friends who lost their loved ones. Such attacks have no place in Europe.\nThe first thing European citizens expect from us is protection. That is also true when it comes to the topic of today's debate: gang violence. Gang violence is not only a big threat to life and security; it is a huge threat to democracy and society too, and it is part of the bigger structures of organised crime infiltrating our legal economies and processes.\nAs outlined by President von der Leyen at the beginning of this mandate, there can be no hiding place for organised crime in Europe, either offline or online. The threat to our internal security by organised crime networks is unprecedented and increasingly visible. And it is not only an impression that we get following the news – the figures speak for themselves. Last year, Europol identified 821 high-risk criminal networks active in the EU. Nearly 90 % of them have infiltrated the legal economy, running businesses, investing in real estate. They are strong and operate freely across borders, including online. They are active in drug trafficking, fraud, property crime, migrant smuggling, and trafficking in human beings. To avoid prosecution, these groups are increasingly recruiting young people to perpetrate even violent crimes.\nMost of this violence is directly linked to organised crime and drug trafficking. Drug-related violence has spread from secluded port areas to the streets of Swedish cities, as criminal organisations fight for control over distribution networks. Innocent bystanders are often caught in this violence, underscoring the urgency of action.\nWe see similar patterns across Europe: drug markets in Brussel's streets, gang wars in Germany and France, threats to port workers in the Netherlands, drug-related killings in Spain and the Western Balkans. This is a global phenomenon that needs to be tackled through stronger cross-border cooperation within the EU and with third countries. Drugs are now Europe's most lucrative criminal market, worth EUR 31 billion annually, and 70 % of organised crime groups use corruption to enable their crimes.\nThe Commission will put forward an EU strategy against corruption. Money is the lifeblood that drives and sustains all these criminal activities. Our response to organised crime must be clear: disrupt their finances, take down their bankers and brokers, tackle the infiltration in the legal economy and disrupt their corrupt networks.\nSince last spring, we have new confiscation rules to eliminate the profits of criminal groups. We need to follow the money to get to those who are behind the crimes. Any investigation should pursue arrests and asset recovery as two sides of the same coin. With Eurojust we need to enhance judicial cooperation within the Union and beyond its borders. The rapid transposition of the new Asset Recovery Directive will provide stronger tools to confiscate illicit profits. It will also strengthen the asset recovery offices to identify, trace and freeze criminal assets.\nThe Commission will step up the fight against serious and organised crime with the forthcoming European internal security strategy. The strategy will cover all forms of organised crime online and offline. We plan to involve all stakeholders in a 'whole of society' approach to be more effective in dismantling high-risk criminal networks and their ringleaders. We will propose to revise the rules to fight organised crime, starting with an updated definition of 'organised crime' and strong investigative tools. The strategy will build on the serious and organised crime threat assessment that Europol will present in the spring. We will enhance Europol support to Member State investigations, especially in areas where the authorities need it the most. We will strengthen Frontex to ensure it can protect our borders in all circumstances.\nAs regards the online dimension, online service providers have a duty to protect their users online. We will continue to strongly enforce the Digital Services Act, which establishes effective measures for tackling illegal content and mitigating societal risks online. And we will continue to step up our efforts in disrupting the recruitment of young people online by organised criminal gangs. Next year we will also set out the framework for an EU critical communication system to strengthen internal security and preparedness.\nWe know that many of the threats to our internal security originate from outside the EU. Security within the Union cannot be achieved without targeted and comprehensive external action through third country partnerships that also benefit our security. The strategy will also address cross-cutting security challenges and hybrid threats such as border management, the weaponisation of migration, and countering sabotage and espionage.\nHonourable Members, as one of the first deliverables of the new internal security strategy, the Commission will launch a new EU action plan against firearms trafficking with more pressure on criminal markets and safeguarding the illicit market. Illicit firearms feed organised crime within the EU, and are regularly used by lone actors. The EU already has rules on the illegal possession and acquisition of firearms and rules on the legal import, export and transit of firearms. However, there are no EU rules on the definition of criminal offences and penalties on firearms-related crimes. This has to change.\nThe fight against drug trafficking must also remain a top priority. For this, it is paramount to tackle the constant inflow of drugs to our continent, mainly through our ports. Over 90 million containers are processed yearly in EU ports. Only a small percentage are inspected, leaving room for criminal exploitation. Sweden, as a major maritime destination and transit country is not immune to this threat. We will build on the work set out in the EU roadmap and the EU Ports Alliance to dismantle criminal business models and to shut down supply routes. Currently, 33 ports, including Helsingborg, Gothenburg and Stockholm are members, and the list is growing.\nThe challenges facing the Union are increasingly complex, interconnected and transnational. This means that we need to approach security in an integrated way, taking all relevant threats, including hybrid ones, into consideration. Internal security is our shared responsibility, and we want the forthcoming strategy to be also the Parliament's strategy. We count on your cooperation to make rapid progress on our common agenda.\n\nTomas Tobé, för PPE gruppen. – Fru talman! Det brutala massmordet i Örebro den svarta dagen den 4 februari var utfört av en enskild gärningsman. Men Sverige är också utsatt för en våldsvåg av sällan skådat slag. Bombningar av hederliga människors bostadshus, närmast dag efter dag, regisserade av hänsynslösa gängkriminella som inte tycks sky några medel.\nDen svenska regeringen genomför nu en helt nödvändig omläggning av rättspolitiken för att krossa gängen. Men vi måste också göra mer på europeisk nivå. 70 % av de kriminella nätverken verkar över gränserna. Gängledare samordnar attacker från utlandet. Vapen och droger flödar. Det sprängs och det skjuts.\nDetta är gränsöverskridande problem som inget medlemsland ska behöva möta ensamt. Därför menar vi i EPP att det nu behövs en europeisk säkerhetspakt mot organiserad brottslighet. Dra in den fria rörligheten för kriminella. Se till att det inte lönar sig att begå brott. Stärk det europeiska polissamarbetet; gör Europol både starkare och operativt.\nVi kan och vi ska göra Sverige och Europa tryggt. Kommissionen har lovat en tuffare strategi mot brottslighet. EPP kommer se till att ni levererar.\n\n Evin Incir, on behalf of the S&D Group. – Madam President, politics must join forces across party lines to break the cycle of violence. This painful reality is the reason why I decided to engage in politics 25 years ago. Since then, the situation has unfortunately only worsened. More children have become both victims and perpetrators to violence.\nLast year alone, 44 people lost their lives to shootings, and, alarmingly, the number of children under 15 suspected of involvement in murder cases surged by 200 % in comparison to the year before in Sweden. Just in the first month of this year, we witnessed 33 bombings. The perpetrators are nowadays so young that the term 'child soldiers' has become a buzzword. Gang violence is creeping down in age, instilling fear in our neighbourhoods and robbing children of their childhood. No one should wake up to a sound of a bomb, instead of a gentle ring of a clock. And let's be clear – no one is born a child soldier.\nOur actions as lawmakers matter. The current Swedish right‑wing and far‑right Government looks to Denmark's hard gang laws – like visitation zones and harsh penalties – but neglects the essential ingredient of Denmark's success: social investments in schools and communities. A school that provides every child with the opportunity to succeed is our most powerful weapon against gang recruitment. It is also absurd that criminals in 2025 can start businesses and exploit the Swedish welfare system, while the parties in government and their supporters in Sweden Democrats are watching.\nWhere is the crisis commission that we have asked for? Also, the EU has an important role in putting an end to the cross‑border gang crime, which poses a serious threat to all our Member States. According to Europol, 70 % of gangs in the EU operate in at least three countries simultaneously. I'm glad that the conservative EPP Group has woken up and realised the importance of acting, but yet they have only presented what they call 'European security pact against organised crime', which is more or less a copy paste of former Commissioner Ylva Johansson's 'EU roadmap to fight organised crime and drug trafficking'.\nInstead of creating new titles on existing measures, we social democrats demand a specific strategy against recruitment, with a coordinator working alongside European authorities such as Europol and Eurojust to prevent children and young people from falling into the claws of the gangs. Politics must unite across party lines, and so must other parts of the society, such as the social media platforms.\nWe therefore need an EU anti‑organised crime law, including addressing the social media platforms responsibilities. It is unacceptable that these platforms are exploited for recruiting child soldiers. Tech giants must be held accountable. Their platforms are today's modern streets and squares. It is about time for the society to get as organised as organised crime. The society must always be stronger than organised crime."


async def llm_calls():
    
    client = OpenAI()

    # Make two parallel calls to OpenAI
    task1 = get_rhetorical_analysis(client, topic_of_debate, gang_violence_debate)
    task2 = get_fact_check(client, topic_of_debate, gang_violence_debate)

    # Task3 is for post analysis of debate
    # task3 = get_argument_map(client, topic_of_debate, gang_violence_debate)
    # results = await asyncio.gather(task1, task2, task3)

    start_time = time.time()
    task_results = await asyncio.gather(task1, task2)
    print("--- Gather response in %s seconds ---" % (time.time() - start_time))

    successful_results = []

    for result in task_results:
        if result and not result.get("error"):
            logger.info(f"JSON response from LLM : {result}")
            successful_results.append(result)

        elif result.get("error"):
            
            logger.info("error occurred while fetching response from LLM, retring...")
            task1 = get_rhetorical_analysis(client, topic_of_debate, gang_violence_debate)
            task2 = get_fact_check(client, topic_of_debate, gang_violence_debate)
            results = await asyncio.gather(task1, task2)
            for result in results:
                if result and not result.get("error"):
                    logger.info(f"JSON response from LLM : {result}")
                    successful_results.append(result)
                elif result.get("error"):
                    logger.info("error occurred again while fetching reponse from LLM. Giving up!")
                else:
                    logger.info("No response or error occurred.")

        else:
            logger.info("No response or error occurred.")

    return successful_results