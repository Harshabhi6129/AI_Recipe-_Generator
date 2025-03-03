from flask import Flask, request, Response
from flask_cors import CORS
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if using a .env file)
load_dotenv()

app = Flask(__name__)
CORS(app)

# Retrieve API key from environment variable
api_key = os.getenv("GENAI_API_KEY")
if not api_key:
    raise ValueError("❌ Google Generative AI API key not found. Set GENAI_API_KEY in environment variables.")

# Configure Google Generative AI API
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

@app.route('/recipeStream', methods=['GET'])
def recipe_stream():
    ingredients = request.args.get("ingredients", "")
    meal_type = request.args.get("mealType", "")
    cuisine = request.args.get("cuisine", "")
    cooking_time = request.args.get("cookingTime", "")
    complexity = request.args.get("complexity", "")
    recipe_name = request.args.get("recipeName", None)

    # If a specific recipe is requested
    if recipe_name:
        prompt = f"Generate a detailed recipe for {recipe_name}. Include ingredients, instructions, and tips."
    else:
        # Generate main recipe and suggestions
        prompt = f"""
        Generate a recipe using the following details:
        Ingredients: {ingredients}
        Meal Type: {meal_type}
        Cuisine Preference: {cuisine}
        Cooking Time: {cooking_time}
        Complexity: {complexity}.
        Provide a detailed recipe. 
        Then, also suggest 3 other similar recipes by name only. 
        Label them as "Other Recipes:" in the output.
        """

    def generate_response():
        try:
            print(f"Sending prompt to Google GenAI: {prompt}")
            response = model.generate_content(prompt)

            content = response.text.split("\n")
            main_recipe = []
            suggestions = []
            is_suggestion_section = False

            for line in content:
                # Check if there's a line indicating the start of suggestions
                if "Other Recipes:" in line or "Similar Recipes:" in line:
                    is_suggestion_section = True
                    continue

                if is_suggestion_section and line.strip():
                    suggestions.append(line.strip())
                elif not is_suggestion_section:
                    main_recipe.append(line.strip())

            # Stream the main recipe content line-by-line
            for chunk in main_recipe:
                if chunk:
                    yield f"data: {chunk}\n\n"

            # Stream suggestions as JSON
            if not recipe_name and suggestions:
                yield f"data: {json.dumps({'suggestions': suggestions})}\n\n"

            # Signal the end of streaming
            yield f"data: {json.dumps({'action': 'close'})}\n\n"

        except Exception as e:
            print(f"Error generating recipe: {e}")
            yield f"data: {json.dumps({'error': f'Failed to generate recipe. Reason: {e}'})}\n\n"

    return Response(generate_response(), content_type="text/event-stream")

if __name__ == "__main__":
    app.run(port=3001, debug=True)
