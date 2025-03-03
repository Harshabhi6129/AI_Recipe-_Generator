import streamlit as st
import openai
import os
from dotenv import load_dotenv
from PIL import Image
import re

# --------------------------
# 1) Environment Setup
# --------------------------
load_dotenv()  # Loads variables from a .env file if present

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("❌ OPENAI_API_KEY not found. Please set it before running.")
    st.stop()

openai.api_key = OPENAI_API_KEY

# --------------------------
# 2) Helper Functions
# --------------------------

def generate_recipe_text(ingredients, meal_type, cuisine, cooking_time, complexity, recipe_name=None):
    """
    Generate a detailed, well-formatted recipe using the OpenAI API.
    If recipe_name is provided, generate a specific detailed recipe.
    Otherwise, generate a recipe based on input details and include exactly 3 alternative recipe suggestions.
    """
    if recipe_name:
        prompt = f"""
You are an expert chef and professional recipe writer. Create a detailed, engaging, and well-structured recipe for "{recipe_name}".
Include:
- A creative, catchy title.
- A clear list of ingredients with precise measurements.
- Step-by-step cooking instructions.
- Useful cooking tips and presentation suggestions.
Ensure the recipe is professionally formatted and easy to follow.
"""
    else:
        prompt = f"""
You are an expert chef and acclaimed recipe writer with a flair for creativity.
Using the details below, generate a comprehensive, well-formatted recipe.

Details:
• Ingredients: {ingredients}
• Meal Type: {meal_type}
• Cuisine Preference: {cuisine}
• Cooking Time: {cooking_time}
• Complexity: {complexity}

Your response should have two sections:

**Main Recipe**:
- A catchy title.
- A detailed list of ingredients with measurements.
- Step-by-step cooking instructions.
- Helpful cooking tips.

**Other Recipe Suggestions**:
After the main recipe, output exactly three alternative recipe names (only names) on separate lines. Each suggestion should be prefixed with a dash ("- "). Label this section clearly with "Other Recipe Suggestions:".

Ensure the entire response is clear, engaging, and professionally formatted.
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

    # Split the response by lines and separate the two sections.
    lines = full_text.split("\n")
    main_recipe_lines = []
    suggestions = []
    is_suggestions_part = False

    for line in lines:
        # Detect the start of suggestions
        if "Other Recipe Suggestions:" in line:
            is_suggestions_part = True
            continue

        if is_suggestions_part:
            if line.strip().startswith("-"):
                # Remove the dash and any extra spaces
                suggestions.append(line.strip()[1:].strip())
            elif line.strip():
                # In case the suggestion doesn't have a dash, add it
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
    Format the recipe text by:
      - Converting recognized section headers (title, main recipe, ingredients, instructions,
        directions, method, tips, etc.) into bold or markdown headings.
      - Using bullet points for ingredients and tips.
      - Using numbered steps for instructions.
      - Keeping the text well-structured and easy to read.
    """

    # We'll define some synonyms for the 'instructions' section to catch variations like "Directions" or "Method".
    instruction_synonyms = ["instructions", "directions", "method"]

    # Headings_map: the key is a word to detect, the value is the markdown heading level.
    # We'll detect them case-insensitively.
    headings_map = {
        "title": "##",
        "main recipe": "##",
        "ingredients": "###",
        "tips": "###",
        "other recipe suggestions": "##"
    }

    lines = recipe_text.split("\n")
    formatted_lines = []

    # We'll store instructions separately so we can turn them into numbered steps.
    instructions_buffer = []
    is_in_instructions_section = False

    current_section = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            # Blank line -> just append and reset
            formatted_lines.append("")
            continue

        lower_line = line_stripped.lower()

        # 1) Check if the line matches any known heading
        # We'll do a quick loop over headings_map
        matched_heading = None
        for heading_key, heading_level in headings_map.items():
            # If the line starts with the heading key (case-insensitive)
            if lower_line.startswith(heading_key):
                matched_heading = heading_level
                break

        # 2) Check if it's an instruction synonym (e.g. "Instructions:", "Method:", etc.)
        if matched_heading is None:  # we haven't matched any heading yet
            for word in instruction_synonyms:
                if lower_line.startswith(word):
                    matched_heading = "###"
                    current_section = "instructions"
                    break

        # 3) If matched a heading, format accordingly and update current_section
        if matched_heading:
            # Output the heading in bold or with "##"
            formatted_lines.append(f"{matched_heading} **{line_stripped}**")

            # Determine if we are in instructions or not
            if "ingredients" in lower_line:
                current_section = "ingredients"
                # If we had instructions stored before, let's flush them (though typically won't happen mid-text)
                if instructions_buffer:
                    formatted_lines.extend(_flush_instructions(instructions_buffer))
            elif "tips" in lower_line:
                current_section = "tips"
                # Flush instructions if any
                if instructions_buffer:
                    formatted_lines.extend(_flush_instructions(instructions_buffer))
            elif "main recipe" in lower_line:
                current_section = "main_recipe"
                if instructions_buffer:
                    formatted_lines.extend(_flush_instructions(instructions_buffer))
            elif "other recipe suggestions" in lower_line:
                current_section = "suggestions"
                if instructions_buffer:
                    formatted_lines.extend(_flush_instructions(instructions_buffer))
            elif any(word in lower_line for word in instruction_synonyms):
                # It's an instruction heading
                current_section = "instructions"
                # If we had instructions from a previous instructions section, let's flush them first
                if instructions_buffer:
                    formatted_lines.extend(_flush_instructions(instructions_buffer))
                # Start a fresh instructions buffer
                instructions_buffer = []
            else:
                # For headings like "Title" etc.
                current_section = "other"
                if instructions_buffer:
                    formatted_lines.extend(_flush_instructions(instructions_buffer))

        else:
            # This line is NOT a heading. Format based on the current section.

            # If we're in instructions, store these lines for final numbering
            if current_section == "instructions":
                instructions_buffer.append(line_stripped)
            
            # If in ingredients or tips, bullet them
            elif current_section == "ingredients" or current_section == "tips":
                # If the line already has a dash or bullet, keep it. Otherwise, add one.
                if re.match(r"^[-*]\s", line_stripped):
                    formatted_lines.append(line_stripped)
                else:
                    formatted_lines.append(f"- {line_stripped}")
            
            else:
                # For sections not specifically known, just keep the text as is
                formatted_lines.append(line_stripped)
    
    # After the loop ends, if there's anything left in instructions_buffer, flush it
    if instructions_buffer:
        formatted_lines.extend(_flush_instructions(instructions_buffer))
        instructions_buffer = []

    # Return the final joined string
    return "\n".join(formatted_lines)

def _flush_instructions(instructions_buffer):
    """
    Convert any collected instructions into a numbered list.
    """
    output = []
    output.append("")  # blank line before the steps
    for idx, step in enumerate(instructions_buffer, start=1):
        output.append(f"{idx}. {step}")
    return output

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
                # Create a tab for each suggestion with improved formatting.
                suggestion_tabs = st.tabs(suggestions)
                for i, tab in enumerate(suggestion_tabs):
                    with tab:
                        st.markdown(f"## **{suggestions[i]}**")
                        with st.spinner(f"Generating detailed recipe for '{suggestions[i]}'..."):
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
                            st.markdown("---")
                            formatted_detailed = format_recipe_text(detailed_text)
                            st.markdown(formatted_detailed)
