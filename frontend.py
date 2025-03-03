import streamlit as st
import openai
import os
from dotenv import load_dotenv
from PIL import Image

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
    Calls the OpenAI API to generate a recipe with a strict, well-formatted layout:
    
    Title:
    <Short Title>

    Ingredients:
    - <Ingredient 1>
    - <Ingredient 2>
    ...

    Instructions:
    1. <Step 1>
    2. <Step 2>
    ...

    Tips:
    - <Tip 1>
    - <Tip 2>
    ...

    Other Recipe Suggestions:
    - <Suggestion 1>
    - <Suggestion 2>
    - <Suggestion 3>
    
    The prompt ensures the model includes exactly these sections.
    Returns (main_recipe_text, suggestions_list).
    """

    if recipe_name:
        # Prompt for a specific recipe
        prompt = f"""
You are an expert chef and recipe writer. Provide a well-structured, thoroughly detailed recipe for "{recipe_name}" in the exact format below:

Title:
<Short Title>

Ingredients:
- <Ingredient 1>
- <Ingredient 2>

Instructions:
1. <Step 1>
2. <Step 2>

Tips:
- <Tip 1>
- <Tip 2>

Other Recipe Suggestions:
- <Suggestion 1>
- <Suggestion 2>
- <Suggestion 3>

Do not deviate from this structure. 
- The "Instructions" must be a numbered list. 
- "Ingredients" must be bullet points. 
- "Tips" must be bullet points. 
- "Other Recipe Suggestions" must have exactly three bullet points.
"""
    else:
        # Prompt for a recipe based on user inputs
        prompt = f"""
You are an expert chef and recipe writer. Provide a well-structured, thoroughly detailed recipe based on the following details:
- Ingredients: {ingredients}
- Meal Type: {meal_type}
- Cuisine Preference: {cuisine}
- Cooking Time: {cooking_time}
- Complexity: {complexity}

Use the exact format below:

Title:
<Short Title>

Ingredients:
- <Ingredient 1>
- <Ingredient 2>

Instructions:
1. <Step 1>
2. <Step 2>

Tips:
- <Tip 1>
- <Tip 2>

Other Recipe Suggestions:
- <Suggestion 1>
- <Suggestion 2>
- <Suggestion 3>

Do not deviate from this structure. 
- The "Instructions" must be a numbered list. 
- "Ingredients" must be bullet points. 
- "Tips" must be bullet points. 
- "Other Recipe Suggestions" must have exactly three bullet points.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional chef and recipe writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        full_text = response['choices'][0]['message']['content']
    except Exception as e:
        return f"ERROR: {e}", []

    # Separate the main recipe from the "Other Recipe Suggestions"
    lines = full_text.split("\n")
    main_recipe_lines = []
    suggestions = []
    is_suggestions_part = False

    for line in lines:
        # Detect the "Other Recipe Suggestions" header
        if line.strip().lower().startswith("other recipe suggestions"):
            is_suggestions_part = True
            continue

        if is_suggestions_part:
            # Each suggestion is expected to start with "- "
            if line.strip().startswith("-"):
                # Remove the dash
                suggestion = line.strip()[1:].strip()
                if suggestion:
                    suggestions.append(suggestion)
        else:
            main_recipe_lines.append(line.rstrip())

    main_recipe_text = "\n".join(main_recipe_lines).strip()
    return main_recipe_text, suggestions

def recognize_ingredients_from_image(image_bytes):
    """
    Placeholder function for image-based ingredient recognition.
    (Implement your image recognition logic or API call here.)
    """
    return None, "❌ Image recognition is not implemented."

def format_recipe_text(recipe_text):
    """
    Parse the recipe text, applying markdown formatting:
    - "Title:" -> bold or heading
    - "Ingredients:" -> heading, bullet points for subsequent lines until next section
    - "Instructions:" -> heading, numbered list for subsequent lines
    - "Tips:" -> heading, bullet points
    - For any line not matching known headings, just show as normal text.
    """

    lines = recipe_text.split("\n")
    formatted_lines = []
    current_section = None
    instruction_steps = []

    for line in lines:
        line_stripped = line.strip()

        # Detect known headings
        if line_stripped.lower().startswith("title:"):
            # Print a heading for the title
            formatted_lines.append("## **Title**")
            # Then print the text after "Title:"
            title_content = line_stripped.split(":", 1)[1].strip()
            if title_content:
                formatted_lines.append(f"**{title_content}**\n")
            current_section = "title"
            continue

        elif line_stripped.lower().startswith("ingredients:"):
            formatted_lines.append("## **Ingredients**")
            current_section = "ingredients"
            continue

        elif line_stripped.lower().startswith("instructions:"):
            formatted_lines.append("## **Instructions**")
            current_section = "instructions"
            # If there's leftover instructions from a previous parse, clear them
            instruction_steps = []
            continue

        elif line_stripped.lower().startswith("tips:"):
            formatted_lines.append("## **Tips**")
            current_section = "tips"
            continue

        elif line_stripped == "":
            # Blank line
            formatted_lines.append("")
            continue

        # Handle content within sections
        if current_section == "ingredients":
            # Expect bullet lines like "- Ingredient"
            if line_stripped.startswith("-"):
                formatted_lines.append(f"- {line_stripped[1:].strip()}")
            else:
                # If user wrote something without a dash, just display it
                formatted_lines.append(f"- {line_stripped}")

        elif current_section == "instructions":
            # Expect numbered lines like "1. Step"
            # If it starts with a digit + ".", we keep it. Otherwise, we add numbering ourselves.
            instruction_steps.append(line_stripped)

        elif current_section == "tips":
            # Expect bullet lines
            if line_stripped.startswith("-"):
                formatted_lines.append(f"- {line_stripped[1:].strip()}")
            else:
                formatted_lines.append(f"- {line_stripped}")

        else:
            # Outside recognized sections: just display as normal text
            formatted_lines.append(line_stripped)

    # After we finish collecting lines, convert instruction_steps into a numbered list
    if instruction_steps:
        for idx, step_line in enumerate(instruction_steps, start=1):
            # If step_line already starts with a digit + ".", keep it
            # Otherwise, add numbering
            step_line_stripped = step_line.strip()
            if step_line_stripped and not step_line_stripped[0].isdigit():
                formatted_lines.append(f"{idx}. {step_line_stripped}")
            else:
                # If the user or model included something like "1." we can just show it
                formatted_lines.append(step_line_stripped)

    return "\n".join(formatted_lines)

# --------------------------
# 3) Streamlit UI
# --------------------------
st.set_page_config(page_title="🍽️ Recipe Generator", layout="wide")

st.title("🍽️ Recipe Generator")
st.subheader("Generate thoroughly structured recipes using OpenAI's API!")

# Input method: typed ingredients vs. uploaded image
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
            # Format and display the main recipe
            formatted_main_recipe = format_recipe_text(main_recipe_text)
            st.markdown("### 📖 **Generated Recipe:**")
            st.markdown(formatted_main_recipe)

            # If there are suggestions, display them in tabs
            if suggestions:
                st.markdown("### 🔍 **Other Recipe Suggestions:**")
                # Each suggestion is just the name of a dish.
                suggestion_tabs = st.tabs(suggestions)
                for i, tab in enumerate(suggestion_tabs):
                    with tab:
                        st.markdown(f"## **{suggestions[i]}**")
                        # Fetch a detailed recipe for each suggestion
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
                            formatted_detailed = format_recipe_text(detailed_text)
                            st.markdown(formatted_detailed)
