import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from PIL import Image

# --------------------------
# 1) Environment Setup
# --------------------------
# Load environment variables (if using a .env file)
load_dotenv()

# Retrieve your GenAI API key from environment variable
API_KEY = os.getenv("GENAI_API_KEY")
if not API_KEY:
    st.error("❌ GENAI_API_KEY not found in environment. Please set it before running.")
    st.stop()

# Configure Google Generative AI
genai.configure(api_key=API_KEY)

# We'll use the flash model, just like your code
model = genai.GenerativeModel("gemini-1.5-flash")


# --------------------------
# 2) Helper Functions
# --------------------------

def generate_recipe_text(ingredients, meal_type, cuisine, cooking_time, complexity, recipe_name=None):
    """
    Calls Google GenAI to generate a recipe. 
    Returns the main recipe and any suggestions as a tuple: (recipe_text, suggestions_list).
    """

    # Create the prompt
    if recipe_name:
        # If a specific recipe is requested
        prompt = f"Generate a detailed recipe for {recipe_name}. Include ingredients, instructions, and tips."
    else:
        # Otherwise, generate main recipe + suggestions
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

    # Call the model
    response = model.generate_content(prompt)
    # Response is a single block of text
    full_text = response.text or ""

    # We'll split lines and look for "Other Recipes:" to separate them
    lines = full_text.split("\n")
    main_recipe_lines = []
    suggestions = []
    is_suggestions_part = False

    for line in lines:
        # Identify suggestion section
        if "Other Recipes:" in line or "Similar Recipes:" in line:
            is_suggestions_part = True
            continue

        if is_suggestions_part:
            # If we are in the suggestion area
            if line.strip():
                suggestions.append(line.strip())
        else:
            # Otherwise, main recipe area
            main_recipe_lines.append(line.strip())

    # Re-join the main recipe text
    recipe_text = "\n".join([ln for ln in main_recipe_lines if ln])
    return recipe_text, suggestions


def recognize_ingredients_from_image(image_bytes):
    """
    Placeholder function. 
    If you have an actual image recognition API, place that call here.
    For now, we'll simply return an error.
    """
    return None, "❌ /recognizeIngredients endpoint or logic isn't implemented."


def format_recipe_text(recipe_text):
    """
    Formats the recipe text with bold headings, bullet points for ingredients and tips,
    and numbered lists for instructions.
    """

    lines = recipe_text.split("\n")
    formatted_lines = []
    current_section = None
    instructions = []
    is_instruction_section = False

    for line in lines:
        line_stripped = line.strip()

        # Detect section headings (Ingredients, Instructions, Tips)
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
        formatted_lines.append("")
        for idx, step in enumerate(instructions, start=1):
            formatted_lines.append(f"{idx}. {step}")

    return "\n".join(formatted_lines)


# --------------------------
# 3) Streamlit UI
# --------------------------

st.set_page_config(page_title="🍽️ Recipe Generator", layout="wide")

st.title("🍽️ Recipe Generator")
st.subheader("Generate delicious recipes based on your ingredients and preferences — **all in one code**!")

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
            st.image(image, caption="Uploaded Image", use_column_width=True)

            # Attempt to "recognize" ingredients from the image
            with st.spinner("🔍 Recognizing ingredients from the image..."):
                image_bytes = uploaded_image.read()
                ingredients_extracted, error = recognize_ingredients_from_image(image_bytes)

            if error:
                st.error(f"❌ Error: {error}")
            else:
                st.success("✅ Ingredients recognized successfully!")
                ingredients = st.text_area(
                    "🛒 Confirm or edit the recognized ingredients:",
                    value=ingredients_extracted,
                    height=150
                )
        except Exception as e:
            st.error(f"❌ Failed to process the uploaded image. Error: {e}")


# Collect other user preferences
col1, col2 = st.columns(2)

with col1:
    meal_type = st.selectbox("🍴 Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"])
    cuisine = st.text_input("🌍 Cuisine Preference (e.g., Italian, Mexican):", "Indian")

with col2:
    cooking_time = st.selectbox("⏰ Cooking Time", ["Less than 30 minutes", "30-60 minutes", "More than 1 hour"])
    complexity = st.selectbox("🔧 Complexity", ["Beginner", "Intermediate", "Advanced"])

# Button to generate the main recipe
generate_button = st.button("✨ Generate Recipe")

# --------------------------
# 4) Generate & Display
# --------------------------

if generate_button:
    if not ingredients:
        st.error("❗ Please enter or upload ingredients to generate a recipe.")
    else:
        with st.spinner("✨ Generating your recipe..."):
            main_recipe_text, suggestions = generate_recipe_text(
                ingredients,
                meal_type,
                cuisine,
                cooking_time,
                complexity
            )

        # Check if there's an error marker in the main recipe (unlikely in this scenario)
        if "ERROR" in main_recipe_text:
            st.error(main_recipe_text)
        else:
            # Format and display the main recipe
            formatted_main_recipe = format_recipe_text(main_recipe_text)
            st.markdown("### 📖 **Generated Recipe:**")
            st.markdown(formatted_main_recipe)

            # If we have suggestions, display them in tabs
            if suggestions:
                st.markdown("### 🔍 **Other Recipe Suggestions:**")
                suggestion_tabs = st.tabs(suggestions)

                for i, tab in enumerate(suggestion_tabs):
                    with tab:
                        # For each suggestion, let's fetch a detailed recipe
                        with st.spinner(f"Fetching details for '{suggestions[i]}'..."):
                            detailed_text, _ = generate_recipe_text(
                                ingredients,
                                meal_type,
                                cuisine,
                                cooking_time,
                                complexity,
                                recipe_name=suggestions[i]
                            )

                        if "ERROR" in detailed_text:
                            st.error(detailed_text)
                        else:
                            formatted_detailed = format_recipe_text(detailed_text)
                            st.markdown(f"#### {suggestions[i]}")
                            st.markdown(formatted_detailed)
