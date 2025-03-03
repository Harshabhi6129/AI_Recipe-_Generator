# frontend.py

import streamlit as st
import requests
import json
from PIL import Image
import io

# -------------
# Helper functions
# -------------

def fetch_recipe(ingredients, meal_type, cuisine, cooking_time, complexity, recipe_name=None):
    """
    Fetches recipe (and suggestions if no recipe_name) from the Flask backend.
    """
    query_params = {
        "ingredients": ingredients,
        "mealType": meal_type,
        "cuisine": cuisine,
        "cookingTime": cooking_time,
        "complexity": complexity,
    }
    if recipe_name:
        query_params["recipeName"] = recipe_name

    try:
        response = requests.get("http://localhost:3001/recipeStream", params=query_params, stream=True, timeout=60)
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to the backend: {e}")
        return "", []

    recipe_lines = []
    suggestions = []

    for chunk in response.iter_lines(decode_unicode=True):
        if chunk:
            text = chunk.lstrip("data: ").strip()
            if not text:
                continue
            try:
                data = json.loads(text)
                # If it's JSON with suggestions
                if "suggestions" in data:
                    suggestions = data["suggestions"]
                elif data.get("action") == "close":
                    break
                elif "error" in data:
                    recipe_lines.append(f"**ERROR**: {data['error']}")
            except json.JSONDecodeError:
                # It's part of the main recipe text
                recipe_lines.append(text)

    # Join the recipe lines
    return "\n".join(recipe_lines), suggestions

def recognize_ingredients_from_image(image_bytes):
    """
    Sends the image to the backend to recognize ingredients.
    """
    url = "http://localhost:3001/recognizeIngredients"
    files = {'image': ('uploaded_image', image_bytes, 'image/jpeg')}
    try:
        response = requests.post(url, files=files, timeout=30)
        if response.status_code == 200:
            data = response.json()
            predictions = data.get('predictions', [])
            if predictions:
                # Extract ingredient names
                ingredients = [pred['ingredient'] for pred in predictions]
                ingredients_str = ', '.join(ingredients)
                return ingredients_str, None
            else:
                return None, 'No ingredients detected.'
        else:
            return None, response.json().get('error', 'Failed to recognize ingredients.')
    except requests.exceptions.RequestException as e:
        return None, str(e)

def format_recipe_text(recipe_text):
    """
    Formats the recipe text with bold headings, bullet points for ingredients and tips,
    and numbered lists for instructions.
    """
    lines = recipe_text.split("\n")
    formatted_lines = []
    current_section = None
    instructions = []
    # To handle instructions separately
    is_instruction_section = False

    for line in lines:
        line_stripped = line.strip()

        # Detect section headings
        if line_stripped.lower().startswith("ingredients"):
            current_section = "ingredients"
            formatted_lines.append(f"**{line_stripped}**")
            continue
        elif line_stripped.lower().startswith("instructions"):
            current_section = "instructions"
            formatted_lines.append(f"**{line_stripped}**")
            is_instruction_section = True
            continue
        elif line_stripped.lower().startswith("tips"):
            current_section = "tips"
            formatted_lines.append(f"**{line_stripped}**")
            continue
        elif line_stripped == "":
            current_section = None
            is_instruction_section = False
            continue

        # Format based on the current section
        if current_section == "ingredients":
            formatted_lines.append(f"- {line_stripped}")
        elif current_section == "instructions":
            instructions.append(line_stripped)
        elif current_section == "tips":
            formatted_lines.append(f"- {line_stripped}")
        else:
            # Any other text outside defined sections remains as plain text
            formatted_lines.append(line_stripped)

    # After processing all lines, handle instructions separately for numbering
    if instructions:
        formatted_lines.append("")  # Add a blank line before instructions
        for idx, step in enumerate(instructions, start=1):
            formatted_lines.append(f"{idx}. {step}")

    return "\n".join(formatted_lines)

# -------------
# Streamlit UI
# -------------

st.set_page_config(page_title="🍽️ Recipe Generator", layout="wide")

st.title("🍽️ Recipe Generator")
st.subheader("Generate delicious recipes based on your ingredients and preferences!")

# Option to choose input method
input_method = st.radio("Select input method:", ("Type Ingredients", "Upload Image"))

ingredients = ""
if input_method == "Type Ingredients":
    # Collect user input
    ingredients = st.text_input("🛒 Enter ingredients (comma-separated):")
else:
    # Image upload
    uploaded_image = st.file_uploader("📷 Upload an image of your ingredients:", type=["png", "jpg", "jpeg"])

    if uploaded_image is not None:
        try:
            # Display the uploaded image
            image = Image.open(uploaded_image)
            st.image(image, caption='Uploaded Image', use_column_width=True)

            # Extract ingredients from the image
            with st.spinner("🔍 Recognizing ingredients from the image..."):
                # Read image file into bytes
                image_bytes = uploaded_image.read()
                ingredients_extracted, error = recognize_ingredients_from_image(image_bytes)

            if error:
                st.error(f"❌ Error: {error}")
            else:
                # Display extracted ingredients and allow user to confirm/edit
                st.success("✅ Ingredients recognized successfully!")
                ingredients = st.text_area(
                    "🛒 Confirm or edit the recognized ingredients:",
                    value=ingredients_extracted,
                    height=150
                )
        except Exception as e:
            st.error(f"❌ Failed to process the uploaded image. Error: {e}")

# Meal preferences
col1, col2 = st.columns(2)
with col1:
    meal_type = st.selectbox("🍴 Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"])
    cuisine = st.text_input("🌍 Cuisine Preference (e.g., Italian, Mexican):")
with col2:
    cooking_time = st.selectbox("⏰ Cooking Time", ["Less than 30 minutes", "30-60 minutes", "More than 1 hour"])
    complexity = st.selectbox("🔧 Complexity", ["Beginner", "Intermediate", "Advanced"])

# Button to generate the main recipe
generate_button = st.button("✨ Generate Recipe")

if generate_button:
    if not ingredients:
        st.error("❗ Please enter or upload ingredients to generate a recipe.")
    else:
        with st.spinner("✨ Generating your recipe..."):
            main_recipe, suggestions = fetch_recipe(
                ingredients, 
                meal_type, 
                cuisine, 
                cooking_time, 
                complexity
            )

    if "ERROR" in main_recipe:
        st.error(main_recipe)
    else:
        # Format and display the main recipe
        formatted_main_recipe = format_recipe_text(main_recipe)
        st.markdown("### 📖 **Generated Recipe:**")
        st.markdown(formatted_main_recipe)

        # If we have suggestions, display them in tabs
        if suggestions:
            st.markdown("### 🔍 **Other Recipe Suggestions:**")
            # Create a tab for each suggestion
            suggestion_tabs = st.tabs(suggestions)

            for i, tab in enumerate(suggestion_tabs):
                with tab:
                    with st.spinner(f"Fetching details for {suggestions[i]}..."):
                        # Fetch the detailed recipe for this suggestion
                        detailed_recipe_text, _ = fetch_recipe(
                            ingredients,
                            meal_type,
                            cuisine,
                            cooking_time,
                            complexity,
                            recipe_name=suggestions[i]
                        )
                    if "ERROR" in detailed_recipe_text:
                        st.error(detailed_recipe_text)
                    else:
                        # Format and display
                        formatted_detailed_recipe = format_recipe_text(detailed_recipe_text)
                        st.markdown(f"#### {suggestions[i]}")
                        st.markdown(formatted_detailed_recipe)
