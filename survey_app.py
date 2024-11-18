import logging
from sanic import Sanic, response
import json
import statistics
import aiohttp
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from sanic_cors import CORS


logging.basicConfig(level=logging.INFO)  
logger = logging.getLogger("SurveyProcessor")


app = Sanic("SurveyProcessor")
# CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "https://magical-profiterole-f67df4.netlify.app"]}})


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")


client = AsyncIOMotorClient(MONGO_URI)
db = client["survey_database"]
collection = db["survey_results"]

GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'

async def generate_description_from_gemini(content):
    headers = {
        "Content-Type": "application/json",
    }

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": content
                    }
                ]
            }
        ]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(GEMINI_API_URL, json=data, headers=headers, params={"key": GEMINI_API_KEY}) as resp:
                result = await resp.json()

                if resp.status == 200:
                    
                    return result['candidates'][0]['content']['parts'][0]['text']
                else:
                    logger.error(f"Gemini API error: {result.get('error', {}).get('message', 'Unknown error')}")
                    return f"Failed to generate description. Error: {result.get('error', {}).get('message', 'Unknown error')}"
        except Exception as e:
            logger.error(f"Exception occurred during Gemini API call: {str(e)}")
            return f"Exception occurred: {str(e)}"


with open("the_value_of_short_hair.txt", "r") as f:
    short_hair_content = f.read()

with open("the_value_of_long_hair.txt", "r") as f:
    long_hair_content = f.read()

def validate_payload(data):
    user_id = data.get("user_id")
    if not isinstance(user_id, str) or len(user_id) < 5:
        return False, "Invalid `user_id`. Must be a string with at least 5 characters."

    survey_results = data.get("survey_results")
    if not isinstance(survey_results, list) or len(survey_results) != 10:
        return False, "`survey_results` must contain exactly 10 entries."

    question_numbers = set()
    for result in survey_results:
        question_number = result.get("question_number")
        question_value = result.get("question_value")

        if not (isinstance(question_number, int) and 1 <= question_number <= 10):
            return False, "Each `question_number` must be an integer between 1 and 10."

        if question_number in question_numbers:
            return False, "Duplicate `question_number` values are not allowed."
        question_numbers.add(question_number)

        if not (isinstance(question_value, int) and 1 <= question_value <= 7):
            return False, "Each `question_value` must be an integer between 1 and 7."

    return True, None


import statistics

def calculate_statistics(survey_results):
    question_values = [result["question_value"] for result in survey_results]
    mean_value = statistics.mean(question_values)
    median_value = statistics.median(question_values)
    std_dev_value = statistics.stdev(question_values) if len(question_values) > 1 else 0  # Avoid error for single value
    
    return {
        "mean": round(mean_value, 2),
        "median": round(median_value, 2),
        "std_dev": round(std_dev_value, 2)
    }




import statistics
from sanic import response

from bson import ObjectId  # Ensure ObjectId is imported from bson

# Utility function to convert ObjectId and other non-JSON serializable items
def convert_objectid(data):
    if isinstance(data, list):
        return [convert_objectid(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_objectid(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data

@app.post("/process-survey")
async def process_survey(request):
    data = request.json

    logger.info(f"Processing survey for user: {data.get('user_id')}")

    # Validate payload
    is_valid, error_message = validate_payload(data)
    if not is_valid:
        logger.warning(f"Invalid payload for user {data.get('user_id')}: {error_message}")
        return response.json({"error": error_message}, status=400)

    survey_results = data.get("survey_results")
    question_values = {item["question_number"]: item["question_value"] for item in survey_results}

    overall_analysis = "unsure" if question_values[1] == 7 and question_values[4] < 3 else "certain"
    cat_dog = "cats" if question_values[10] > 5 and question_values[9] <= 5 else "dogs"
    avg_value = statistics.mean([item["question_value"] for item in survey_results])
    fur_value = "long" if avg_value > 5 else "short"
    tail_value = "long" if question_values[7] > 4 else "short"

    content = short_hair_content if avg_value > 4 else long_hair_content
    description = await generate_description_from_gemini(content)
    clean_description = description.replace('\n', '').strip()

    stats = {
        "mean": round(statistics.mean([item["question_value"] for item in survey_results]), 2),
        "median": round(statistics.median([item["question_value"] for item in survey_results]), 2),
        "std_dev": round(statistics.stdev([item["question_value"] for item in survey_results]) if len(survey_results) > 1 else 0, 2)
    }

    result = {
        "user_id": data.get("user_id"),
        "overall_analysis": overall_analysis,
        "cat_dog": cat_dog,
        "fur_value": fur_value,
        "tail_value": tail_value,
        "description": clean_description,
        "statistics": stats  
    }

    try:
        insert_result = await collection.insert_one(result)
        result["db_id"] = insert_result.inserted_id  # Keep ObjectId in result for now
        logger.info(f"Survey processed successfully for user {data.get('user_id')}, inserted ID: {result['db_id']}")
    except Exception as e:
        logger.error(f"Failed to save data to the database for user {data.get('user_id')}: {str(e)}")
        return response.json({"error": f"Failed to save data to the database: {str(e)}"}, status=500)

    # Convert all ObjectId fields to strings before sending the response
    return response.json(convert_objectid(result), status=200)



# @app.post("/process-survey")
# async def process_survey(request):
#     data = request.json

#     logger.info(f"Processing survey for user: {data.get('user_id')}")

#     # Validate payload
#     is_valid, error_message = validate_payload(data)
#     if not is_valid:
#         logger.warning(f"Invalid payload for user {data.get('user_id')}: {error_message}")
#         return response.json({"error": error_message}, status=400)

#     survey_results = data.get("survey_results")
#     question_values = {item["question_number"]: item["question_value"] for item in survey_results}


#     overall_analysis = "unsure" if question_values[1] == 7 and question_values[4] < 3 else "certain"
#     cat_dog = "cats" if question_values[10] > 5 and question_values[9] <= 5 else "dogs"
#     avg_value = statistics.mean([item["question_value"] for item in survey_results])
#     fur_value = "long" if avg_value > 5 else "short"
#     tail_value = "long" if question_values[7] > 4 else "short"

#     content = short_hair_content if avg_value > 4 else long_hair_content
#     description = await generate_description_from_gemini(content)
#     clean_description = description.replace('\n', '').strip()


#     stats = {
#         "mean": round(statistics.mean([item["question_value"] for item in survey_results]), 2),
#         "median": round(statistics.median([item["question_value"] for item in survey_results]), 2),
#         "std_dev": round(statistics.stdev([item["question_value"] for item in survey_results]) if len(survey_results) > 1 else 0, 2)
#     }

#     result = {
#         "user_id": data.get("user_id"),
#         "overall_analysis": overall_analysis,
#         "cat_dog": cat_dog,
#         "fur_value": fur_value,
#         "tail_value": tail_value,
#         "description": clean_description,
#         "statistics": stats  
#     }

#     try:
#         insert_result = await collection.insert_one(result)
#         result["db_id"] = str(insert_result.inserted_id)
#         logger.info(f"Survey processed successfully for user {data.get('user_id')}, inserted ID: {result['db_id']}")
#     except Exception as e:
#         logger.error(f"Failed to save data to the database for user {data.get('user_id')}: {str(e)}")
#         return response.json({"error": f"Failed to save data to the database: {str(e)}"}, status=500)

#     return response.json(result, status=200)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

