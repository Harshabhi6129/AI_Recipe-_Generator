import streamlit as st
import openai
import os
from dotenv import load_dotenv
from PIL import Image

# --------------------------
# 1) Environment Setup
# --------------------------
load_dotenv()  # Load variables from .env if available

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("❌ OPENAI_API_KEY not found in environment. Please set it before running.")
    st.stop()

openai.api_key = OPENAI_API_KEY

# --------------------------
# 2) Helper Functions
# --------------------------

def generate_recipe_text(ingredients, meal_type, cuisine, cooking_time, complexity, recipe_name=None):
    """
    Generate a detailed, well-formatted recipe (and suggestions) using the OpenAI API.
    When recipe_name is provided, generate a specific detailed recipe.
    Otherwise, generate a recipe based on input details and list 3 similar recipe suggestions.
    """
    if recipe_name:
        prompt = f"""
You are an expert chef and an acclaimed recipe writer. Create a detailed, engaging, and well-structured recipe for "{recipe_name}".
Include:
- A creative and catchy title.
- A clear list of ingredients with measurements.
- Step-by-step instructions.
- Useful cooking tips and suggestions for presentation or enhancement.
Ensure the recipe is professional, detailed, and formatted for easy reading.
"""
    else:
        prompt = f"""
You are an expert chef and an acclaimed recipe writer with a flair for creativity.
Using the details below, generate a comprehensive, well-formatted recipe:
• Ingredients: {ingredients}
• Meal Type: {meal_type}
• Cuisine Preference: {cuisine}
• Cooking Time: {cooking_time}
• Complexity: {complexity}

Your response should include:
1. A catchy title.
2. A detailed list of ingredients with precise measurements.
3. Step-by-step cooking instructions.
4. Helpful cooking tips.
5. After the main recipe, list 3 creative, similar recipe suggestions (names only) under the header "Other Recipe Suggestions:".
Make sure the recipe is clear, engaging, and professional.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional chef and recipe writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800,
        )
        full_text = response['choices'][0]['message']['content']
    except Exception as e:
        return f"ERROR: {e}", []

    # Split the response to separate the main recipe from the suggestions.
    lines = full_text.split("\n")
    main_recipe_lines = []
    suggestions = []
    is_suggestions_part = False

    for line in lines:
        if "Other Recipe Suggestions:" in line:
            is_suggestions_part = True
            continue
        if is_suggestions_part:
            if line.strip():
                suggestions.append(line.strip())
        else:
            main_recipe_lines.append(line.strip())

    recipe_text = "\n".join([ln for ln in main_recipe_lines if ln])
    return recipe_text, suggestions

def recognize_ingredients_from_image(image_bytes):
    """
    Placeholder function for image-based ingredient recognition.
    (Implement your image recognition logic or API call here.)
    """
    return None, "❌ Image recognition is not implemented."

def format_recipe_text(recipe_text):
    """
    Format the recipe text into bold headings for sections, bullet lists for ingredients/tips,
    and numbered steps for instructions.
    """
    lines = recipe_text.split("\n")
    formatted_lines = []
    current_section = None
    instructions = []
    is_instruction_section = False

    for line in lines:
        line_stripped = line.strip()
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

        if current_section == "ingredients":
            formatted_lines.append(f"- {line_stripped}")
        elif current_section == "instructions":
            instructions.append(line_stripped)
        elif current_section == "tips":
            formatted_lines.append(f"- {line_stripped}")
        else:
            formatted_lines.append(line_stripped)

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
st.subheader("Generate detailed and professional recipes using OpenAI's API!")

input_method = st.radio("Select input method:", ("Type Ingredients", "Upload Image"))

ingredients = ""
if input_method == "Type Ingredients":
    ingredients = st.text_input("🛒 Enter ingredients (comma-separated):")
else:
    uploaded_image = st.file_uploader("📷 Upload an image of your ingredients:", type=["png", "jpg", "jpeg"])
    if uploaded_image is not None:
        try:
            image = Image.open(uploaded_image)
            st.image(image, caption="Uploaded Image", use_column_width=True)
            with st.spinner("🔍 Recognizing ingredients from the image..."):
                image_bytes = uploaded_image.read()
                ingredients_extracted, error = recognize_ingredients_from_image(image_bytes)
            if error:
                st.error(f"❌ Error: {error}")
            else:
                st.success("✅ Ingredients recognized successfully!")
                ingredients = st.text_area("🛒 Confirm or edit the recognized ingredients:",
                                            value=ingredients_extracted, height=150)
        except Exception as e:
            st.error(f"❌ Failed to process the uploaded image. Error: {e}")

col1, col2 = st.columns(2)
with col1:
    meal_type = st.selectbox("🍴 Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"])
    cuisine = st.text_input("🌍 Cuisine Preference (e.g., Italian, Mexican):", "Indian")
with col2:
    cooking_time = st.selectbox("⏰ Cooking Time", ["Less than 30 minutes", "30-60 minutes", "More than 1 hour"])
    complexity = st.selectbox("🔧 Complexity", ["Beginner", "Intermediate", "Advanced"])

generate_button = st.button("✨ Generate Recipe")

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
        if "ERROR" in main_recipe_text:
            st.error(main_recipe_text)
        else:
            formatted_main_recipe = format_recipe_text(main_recipe_text)
            st.markdown("### 📖 **Generated Recipe:**")
            st.markdown(formatted_main_recipe)

            if suggestions:
                st.markdown("### 🔍 **Other Recipe Suggestions:**")
                suggestion_tabs = st.tabs(suggestions)
                for i, tab in enumerate(suggestion_tabs):
                    with tab:
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
