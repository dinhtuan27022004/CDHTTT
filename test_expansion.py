
from services.query_expansion import generate_similar_questions
import os
from dotenv import load_dotenv

load_dotenv()

question = "lấy trộm xe máy bị phạt thế nào?"
print(f"Original Question: {question}")
results = generate_similar_questions(question)
print(f"Results: {results}")

if len(results) > 1:
    print("SUCCESS: Generated similar questions.")
else:
    print("FAILURE: No similar questions generated.")
