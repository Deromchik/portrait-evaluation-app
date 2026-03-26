import streamlit as st
import json
import base64
import requests
import time
from pathlib import Path
from datetime import datetime

# OpenRouter completion cap (comparison JSON can exceed 6k tokens)
OPENROUTER_MAX_TOKENS = 12000

# Page configuration
st.set_page_config(
    page_title="Portrait Evaluation Assistant",
    page_icon="🎨",
    layout="wide"
)

# CSS styles - Light theme with dark text
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 50%, #d9dfe5 100%);
    }
    
    .main-title {
        font-family: 'Playfair Display', Georgia, serif;
        color: #2c3e50;
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        text-shadow: 1px 1px 2px rgba(255,255,255,0.5);
    }
    
    .subtitle {
        color: #546e7a;
        text-align: center;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    
    .iteration-card {
        background: rgba(255,255,255,0.8);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #3498db;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .score-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: bold;
        margin: 0.25rem;
    }
    
    .score-high { background: #d4edda; color: #155724; }
    .score-mid { background: #fff3cd; color: #856404; }
    .score-low { background: #f8d7da; color: #721c24; }
    
    .chat-message {
        padding: 1rem;
        border-radius: 12px;
        margin: 0.5rem 0;
    }
    
    .user-message {
        background: rgba(52, 152, 219, 0.1);
        border: 1px solid rgba(52, 152, 219, 0.3);
    }
    
    .assistant-message {
        background: rgba(46, 204, 113, 0.1);
        border: 1px solid rgba(46, 204, 113, 0.3);
    }
    
    /* Make text more readable */
    .stMarkdown, .stText, p, span, div {
        color: #2c3e50;
    }
    
    .stExpander {
        background: rgba(255,255,255,0.9);
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Prompts - Pre-filter agents (agent1, agent2, agent3)
AGENT1_INITIAL_ANALYSIS = """### Task:
You are provided with an image from a painting student. Your task is to analyze the uploaded image and classify its contents. Based on your analysis, return a JSON-formatted output containing the following variables:

### Output Format:
The output should be a JSON object with the following structure:
{{
    "OBJECT_ON_IMAGE": "<String>",
    "IS_PORTRAIT": <Bool>,
    "CENCORED_CONTENT": <Bool>,
    "PAINTING_OR_DRAWING_OR_ELSE": "<String>",
    "DRAWING_STYLE": "<String>"
}}

### Variables:
1. **OBJECT_ON_IMAGE**: A string describing the objects visible on the image.
2. **IS_PORTRAIT**: A Boolean value indicating whether the image contains a portrait.
   - Return `True` if the image contains a portrait (i.e., focuses on a person's face or upper body).
   - Return `False` if the image does not contains a portrait.
3. **CENCORED_CONTENT**: A Boolean value indicating whether the image contains censored content.
   - Return `True` if the image includes censored content such as nudity, explicit material, or other sensitive elements.
   - Return `False` if the image does not contain censored content.
4. **PAINTING_OR_DRAWING_OR_ELSE**: A string indicating the type of the artwork.
   - Return `"Painting"` if the image is of a painting (i.e., an artwork created using paints, such as oil, acrylic, or watercolor).
   - Return `"Drawing"` if the image is of a drawing (i.e., an artwork created using dry media like pencils, charcoal, or ink).
   - Return `"Manga"` if the image is of a manga style drawing or painting.
   - Return `"Cartoon"` if the image is of a cartoon style drawing or painting.
   - Return `"Else"` if the image is neither a painting nor a drawing.
5. **DRAWING_STYLE**: A string indicating the style of the drawing.

### Rules:
- Always provide concise and accurate descriptions for the "OBJECT_ON_IMAGE".
- Ensure the Boolean values for "IS_PORTRAIT" and "CENCORED_CONTENT" are accurate based on the image content.
- Correctly classify the image type in "PAINTING_OR_DRAWING_OR_ELSE" according to the visual cues.
- Carefully examine the input image to ensure the accuracy of the output format in JSON.
- If unsure about any classification, use your best judgment based on the image content.
"""
AGENT2_CENSORED_MESSAGE = """### Task:
You were provided with an image from a painting student. Your task was to analyze the image and classify its contents. Based on your analysis, you have found that the image has censored content.
This was your output:
{input_data}

Your task is to write a message in {output_language} explaining that this censored content is not allowed. Maximum amount of characters is 300.
"""
AGENT3_NOT_PORTRAIT_MESSAGE = """### Task:
You were provided with an image from a painting student. Your task was to analyze the image and classify its contents. Based on your analysis, you have found that the image does not contain a portrait.
This was your output:
{input_data}

Your task is to write a message in {output_language} explaining that at the moment you only provide painting lessons for portraits. Maximum amount of characters is 300.
"""

from portrait_prompts import (
    AUDIENCE_COMPLEXITY,
    AUDIENCE_COMPLEXITY_BEGINNER,
    COMPARISON_PROMPT,
    EVALUATE_PORTRAIT_STANDALONE,
    JULIA_STYLE_RULES,
)


# Initialize session state
if "iterations" not in st.session_state:
    st.session_state.iterations = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "output_language" not in st.session_state:
    st.session_state.output_language = "English"

if "skill_level" not in st.session_state:
    st.session_state.skill_level = "beginner"

if "reasoning_effort" not in st.session_state:
    # OpenRouter reasoning effort for GPT-5 models (reasoning: {effort: ...})
    # Default is "none" to avoid extra latency/cost unless the user picks otherwise.
    st.session_state.reasoning_effort = "none"

if "standalone_model" not in st.session_state:
    st.session_state.standalone_model = "openai/gpt-5.4-nano"

if "comparison_model" not in st.session_state:
    st.session_state.comparison_model = "openai/gpt-5.4-nano"

# Pre-filter agents (agent1, agent2, agent3) - fast/cheap model for classification tasks
if "prefilter_model" not in st.session_state:
    st.session_state.prefilter_model = "openai/gpt-4o-mini"


# API key from Streamlit secrets
API_KEY = st.secrets["OPENAI_API_KEY"]


def encode_image_to_base64(uploaded_file):
    """Converts uploaded file to base64"""
    bytes_data = uploaded_file.getvalue()
    encoded = base64.b64encode(bytes_data).decode('utf-8')

    # Determine MIME type
    file_type = uploaded_file.type or "image/jpeg"
    return f"data:{file_type};base64,{encoded}"


def get_comparison_data(iterations):
    """Returns data for comparison"""
    n = len(iterations)

    if n == 1:
        return {"first": None, "previous": None, "current": iterations[0]}
    elif n == 2:
        return {"first": iterations[0], "previous": None, "current": iterations[1]}
    else:
        return {"first": iterations[0], "previous": iterations[n-2], "current": iterations[n-1]}


def call_agent1_initial_analysis(api_key, image_base64, model="openai/gpt-4o-mini"):
    """Agent1: Initial image analysis - classifies portrait, censored, etc. Takes image as input."""
    user_content = [
        {"type": "text", "text": "Analyze this image and return the classification JSON."},
        {"type": "image_url", "image_url": {"url": image_base64, "detail": "low"}}
    ]
    return call_openai_api(api_key, AGENT1_INITIAL_ANALYSIS, user_content, model=model)


def call_agent2_censored_message(api_key, agent1_output_json, output_language="English", model="openai/gpt-4o-mini"):
    """Agent2: Generates censored content rejection message. Text-only input."""
    prompt = AGENT2_CENSORED_MESSAGE.format(
        input_data=agent1_output_json, output_language=output_language)
    return call_openai_api(api_key, prompt, user_content="Generate the rejection message.", model=model)


def call_agent3_not_portrait_message(api_key, agent1_output_json, output_language="English", model="openai/gpt-4o-mini"):
    """Agent3: Generates not-portrait rejection message. Text-only input."""
    prompt = AGENT3_NOT_PORTRAIT_MESSAGE.format(
        input_data=agent1_output_json, output_language=output_language)
    return call_openai_api(api_key, prompt, user_content="Generate the rejection message.", model=model)


def parse_agent1_response(response_text):
    """Parse agent1 JSON response. Returns dict or None."""
    try:
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            return json.loads(response_text[start_idx:end_idx])
    except json.JSONDecodeError:
        pass
    return None


def call_openai_api(api_key, system_prompt, user_content=None, model="openai/gpt-5.2",
                      response_format=None):
    """Call OpenAI API (via OpenRouter)"""
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",  # Client URL
        "X-Title": "Portrait Evaluation Assistant"  # Client title
    }

    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": system_prompt}
            ],
        }
    ]

    # Optionally add user message
    if user_content is not None:
        messages.append({"role": "user", "content": user_content})

    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": OPENROUTER_MAX_TOKENS
    }

    if response_format is not None:
        data["response_format"] = response_format

    # Optionally control reasoning effort (OpenRouter uses `reasoning: {effort: ...}`)
    if model.startswith("openai/gpt-5") and "reasoning_effort" in st.session_state:
        data["reasoning"] = {"effort": st.session_state.reasoning_effort}

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()

    result = response.json()
    return result["choices"][0]["message"]["content"], result.get("usage", {})


def build_standalone_content(image_base64):
    """Builds content for standalone evaluation"""
    return [
        {"type": "text", "text": "This is a portrait painted by a student. Please evaluate it."},
        {"type": "image_url", "image_url": {"url": image_base64, "detail": "high"}}
    ]


def build_comparison_content(comparison_data):
    """Builds content for comparison"""
    user_content = []

    # First iteration
    if comparison_data["first"]:
        first = comparison_data["first"]
        user_content.append(
            {"type": "text", "text": "=== FIRST ITERATION (Initial Portrait) ==="})
        user_content.append({"type": "image_url", "image_url": {
                            "url": first["image_base64"], "detail": "high"}})
        user_content.append(
            {"type": "text", "text": f"First iteration expert evaluation:\n{json.dumps(first['evaluation'], indent=2, ensure_ascii=False)}"})

    # Previous iteration
    if comparison_data["previous"]:
        previous = comparison_data["previous"]
        user_content.append(
            {"type": "text", "text": "=== PREVIOUS ITERATION (Most Recent Before Current) ==="})
        user_content.append({"type": "image_url", "image_url": {
                            "url": previous["image_base64"], "detail": "high"}})
        user_content.append(
            {"type": "text", "text": f"Previous iteration expert evaluation:\n{json.dumps(previous['evaluation'], indent=2, ensure_ascii=False)}"})

    # Current iteration
    current = comparison_data["current"]
    user_content.append(
        {"type": "text", "text": "=== CURRENT ITERATION (To Be Evaluated) ==="})
    user_content.append({"type": "image_url", "image_url": {
                        "url": current["image_base64"], "detail": "high"}})
    user_content.append(
        {"type": "text", "text": "Please analyze the current portrait, compare it with the previous iterations, and provide a comprehensive evaluation."})

    return user_content


def parse_evaluation_response(response_text, is_comparison=False):
    """Parses API response"""
    try:
        # Try to find JSON in response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    return None


def extract_standard_evaluation(parsed_response, is_comparison=False):
    """Extracts standard evaluation format from response"""
    if not parsed_response:
        return None

    categories = [
        "Composition and Design", "Proportions and Anatomy", "Perspective and Depth",
        "Use of Light and Shadow", "Color Theory and Application", "Brushwork and Technique",
        "Expression and Emotion", "Creativity and Originality", "Attention to Detail", "Overall Impact"
    ]

    standard_eval = {}

    for category in categories:
        if category in parsed_response:
            cat_data = parsed_response[category]
            if is_comparison and "current_score" in cat_data:
                standard_eval[category] = {
                    "score": cat_data.get("current_score"),
                    "feedback": cat_data.get("feedback", "")
                }
            elif "score" in cat_data:
                standard_eval[category] = {
                    "score": cat_data.get("score"),
                    "feedback": cat_data.get("feedback", "")
                }

    return standard_eval if standard_eval else None


def calculate_average_score(evaluation):
    """Calculates average score"""
    if not evaluation:
        return 0
    scores = [v.get("score", 0) for v in evaluation.values()
              if isinstance(v, dict) and "score" in v]
    return sum(scores) / len(scores) if scores else 0


def get_score_class(score):
    """Returns CSS class for score"""
    if score >= 7:
        return "score-high"
    elif score >= 5:
        return "score-mid"
    return "score-low"


def get_export_data(iterations):
    """Prepares data for export (without images)"""
    export_list = []
    for i, iteration in enumerate(iterations):
        export_item = {
            "iteration": i + 1,
            "image_name": iteration.get("image_name", "Unknown"),
            "timestamp": iteration.get("timestamp", "N/A"),
            "evaluation": iteration.get("evaluation"),
            "parsed_response": iteration.get("parsed_response"),
            "raw_response": iteration.get("raw_response"),
        }
        export_list.append(export_item)
    return export_list


def get_full_logs(iterations):
    """Prepares complete API logs for export (without base64 images)"""
    logs = {
        "export_timestamp": datetime.now().isoformat(),
        "total_iterations": len(iterations),
        "iterations": []
    }

    for i, iteration in enumerate(iterations):
        is_comparison = i > 0

        # Build user content description (without base64)
        if is_comparison:
            # Get comparison data for this iteration
            comparison_info = {
                "first_iteration": {
                    "image_name": iterations[0].get("image_name", "Unknown"),
                    "evaluation": iterations[0].get("evaluation")
                },
                "previous_iteration": {
                    "image_name": iterations[i-1].get("image_name", "Unknown") if i > 1 else None,
                    "evaluation": iterations[i-1].get("evaluation") if i > 1 else None
                } if i > 1 else None,
                "current_iteration": {
                    "image_name": iteration.get("image_name", "Unknown")
                }
            }
            user_content_log = {
                "type": "comparison",
                "comparison_data": comparison_info
            }
        else:
            user_content_log = {
                "type": "standalone",
                "image_name": iteration.get("image_name", "Unknown")
            }

        # Get actual system_prompt that was sent to API (with substituted variables)
        actual_system_prompt = iteration.get("system_prompt")
        if not actual_system_prompt:
            # Fallback to template name if not saved
            actual_system_prompt = "COMPARISON_PROMPT" if is_comparison else "EVALUATE_PORTRAIT_STANDALONE"

        # Get model used for this iteration
        model_used = iteration.get("model", "openai/gpt-5.2")

        iteration_log = {
            "iteration_number": i + 1,
            "timestamp": iteration.get("timestamp", "N/A"),
            "image_name": iteration.get("image_name", "Unknown"),
            "mode": "comparison" if is_comparison else "standalone",
            "api_input": {
                "model": model_used,
                "temperature": 0.1,
                "max_tokens": OPENROUTER_MAX_TOKENS,
                "reasoning_effort": "none" if model_used == "openai/gpt-5.2" else None,
                # Use actual prompt with substituted variables
                "system_prompt": actual_system_prompt,
                "user_content": user_content_log
            },
            "api_output": {
                "raw_response": iteration.get("raw_response"),
                "parsed_response": iteration.get("parsed_response"),
                "evaluation": iteration.get("evaluation")
            }
        }

        logs["iterations"].append(iteration_log)

    return logs


def display_evaluation(evaluation, is_comparison=False, parsed_response=None, raw_response=None):
    """Displays evaluation"""
    if not evaluation:
        st.warning("Could not parse evaluation")
        return

    # Show progress_summary if available
    if is_comparison and parsed_response and "progress_summary" in parsed_response:
        summary = parsed_response["progress_summary"]
        st.markdown("### 📈 Progress")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(
                f"**Overall Progress:**\n{summary.get('overall_improvement', 'N/A')}")
        with col2:
            st.success(
                f"**Recent Changes:**\n{summary.get('recent_changes', 'N/A')}")
        with col3:
            st.warning(
                f"**Self-Initiated:**\n{summary.get('self_initiated_improvements', 'N/A')}")

    # Show average score
    avg_score = calculate_average_score(evaluation)
    st.markdown(f"### Average Score: **{avg_score:.1f}**/10")

    # Show scores by category
    cols = st.columns(2)
    categories = list(evaluation.keys())

    for i, category in enumerate(categories):
        if isinstance(evaluation[category], dict) and "score" in evaluation[category]:
            data = evaluation[category]
            with cols[i % 2]:
                score = data.get("score", 0)
                score_class = get_score_class(score)

                with st.expander(f"**{category}** - {score}/10", expanded=False):
                    st.markdown(
                        f"<span class='score-badge {score_class}'>{score}/10</span>", unsafe_allow_html=True)
                    st.write(data.get("feedback", ""))

    # Show raw JSON option
    if raw_response:
        with st.expander("📄 View Raw JSON Response", expanded=False):
            st.code(raw_response, language="json")


# === MAIN INTERFACE ===

st.markdown("<h1 class='main-title'>🎨 Portrait Evaluation Assistant</h1>",
            unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Upload portraits and receive professional feedback with progress tracking</p>", unsafe_allow_html=True)

# Sidebar for statistics only (no API key)
with st.sidebar:
    st.header("📊 Statistics")
    st.metric("Number of Iterations", len(st.session_state.iterations))

    if st.session_state.iterations:
        first_avg = calculate_average_score(
            st.session_state.iterations[0].get("evaluation"))
        last_avg = calculate_average_score(
            st.session_state.iterations[-1].get("evaluation"))
        delta = last_avg - first_avg if last_avg and first_avg else 0

        st.metric("First Score", f"{first_avg:.1f}" if first_avg else "N/A")
        st.metric("Latest Score", f"{last_avg:.1f}" if last_avg else "N/A",
                  delta=f"{delta:+.1f}" if delta else None)

    st.divider()

    if st.button("🗑️ Clear History", type="secondary"):
        st.session_state.iterations = []
        st.session_state.chat_history = []
        st.rerun()

    # Export data (without images)
    if st.session_state.iterations:
        export_data = get_export_data(st.session_state.iterations)
        export_json = json.dumps(
            export_data, indent=2, ensure_ascii=False, default=str)
        st.download_button(
            "📥 Export History",
            export_json,
            file_name=f"portrait_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

        # Export full logs
        full_logs = get_full_logs(st.session_state.iterations)
        full_logs_json = json.dumps(
            full_logs, indent=2, ensure_ascii=False, default=str)
        st.download_button(
            "📋 Export Full Logs",
            full_logs_json,
            file_name=f"portrait_full_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

# Main content
col_main, col_history = st.columns([2, 1])

with col_main:
    st.header("⚙️ Settings")

    # Model selection for evaluation prompts (vision-capable, fast)
    model_options = [
        "openai/gpt-5.2",
        "openai/gpt-4o-mini",
        "openai/gpt-5.4-nano",
        "openai/gpt-5.4-mini",
        "xiaomi/mimo-v2-omni",
        "mistralai/mistral-small-2603",
        "google/gemini-3.1-flash-lite-preview",
        "google/gemini-3.1-flash-image-preview",
        "qwen/qwen3.5-35b-a3b",
    ]

    col_model1, col_model2 = st.columns(2)

    with col_model1:
        selected_standalone_model = st.selectbox(
            "Model for Standalone Evaluation",
            options=model_options,
            index=model_options.index(
                st.session_state.standalone_model) if st.session_state.standalone_model in model_options else 0,
            help="Select the model for first portrait evaluation"
        )
        st.session_state.standalone_model = selected_standalone_model

    with col_model2:
        selected_comparison_model = st.selectbox(
            "Model for Comparison Evaluation",
            options=model_options,
            index=model_options.index(
                st.session_state.comparison_model) if st.session_state.comparison_model in model_options else 0,
            help="Select the model for comparison evaluations"
        )
        st.session_state.comparison_model = selected_comparison_model

    # Pre-filter model (agent1, agent2, agent3) - fast/cheap for classification
    prefilter_options = ["openai/gpt-4o-mini",
                         "openai/gpt-4.1-nano", "openai/gpt-4o", "openai/gpt-5.2"]
    selected_prefilter = st.selectbox(
        "Model for Image Check (agent1/2/3)",
        options=prefilter_options,
        index=prefilter_options.index(
            st.session_state.prefilter_model) if st.session_state.prefilter_model in prefilter_options else 0,
        help="Fast model for initial image classification (portrait/censored check). Default: gpt-4o-mini"
    )
    st.session_state.prefilter_model = selected_prefilter

    st.divider()

    # Reasoning effort (GPT-5 models only; OpenRouter normalizes this as `reasoning.effort`)
    reasoning_effort_options = ["xhigh", "high", "medium", "low", "minimal", "none"]
    selected_reasoning_effort = st.selectbox(
        "Reasoning effort (GPT-5)",
        options=reasoning_effort_options,
        index=reasoning_effort_options.index(st.session_state.reasoning_effort)
        if st.session_state.reasoning_effort in reasoning_effort_options else 0,
        help="Controls how much effort GPT-5 models spend on reasoning. Higher can improve quality but may be slower/costlier."
    )
    st.session_state.reasoning_effort = selected_reasoning_effort

    st.divider()

    # Language selector
    language_options = {
        "English": "English",
        "Ukrainian": "Ukrainian",
        "Russian": "Russian",
        "Spanish": "Spanish",
        "French": "French",
        "German": "German"
    }

    selected_language = st.selectbox(
        "Output Language",
        options=list(language_options.keys()),
        index=list(language_options.keys()).index(
            st.session_state.output_language) if st.session_state.output_language in language_options else 0,
        help="Select the language for evaluation feedback"
    )
    st.session_state.output_language = selected_language

    # Skill level (audience complexity)
    skill_level_options = ["beginner", "hobbyist", "trained/advanced"]
    selected_skill_level = st.selectbox(
        "Skill Level (Audience)",
        options=skill_level_options,
        index=skill_level_options.index(
            st.session_state.skill_level) if st.session_state.skill_level in skill_level_options else 0,
        help="Beginner: very simple words, 12-14 yo. Hobbyist: accessible with some art terms. Trained/Advanced: professional terminology, deeper analysis."
    )
    st.session_state.skill_level = selected_skill_level

    st.divider()

    st.header("📤 Upload Portrait")

    uploaded_file = st.file_uploader(
        "Select portrait image",
        type=["jpg", "jpeg", "png", "webp"],
        help="Supported formats: JPG, PNG, WEBP"
    )

    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded portrait",
                 use_container_width=True)

        if st.button("🚀 Get Evaluation", type="primary"):
            time_start = time.perf_counter()
            with st.spinner("Analyzing portrait..."):
                try:
                    iteration_added = False
                    # Encode image
                    image_base64 = encode_image_to_base64(uploaded_file)

                    # Agent1: Initial analysis (first gate - image classification)
                    with st.spinner("Checking image..."):
                        agent1_text, _ = call_agent1_initial_analysis(
                            API_KEY, image_base64,
                            model=st.session_state.prefilter_model
                        )
                    agent1_data = parse_agent1_response(agent1_text)
                    prefilter_passed = True

                    if agent1_data:
                        # Agent2: Censored content → reject
                        if agent1_data.get("CENCORED_CONTENT") is True:
                            agent2_text, _ = call_agent2_censored_message(
                                API_KEY, json.dumps(agent1_data, indent=2),
                                output_language=st.session_state.output_language,
                                model=st.session_state.prefilter_model
                            )
                            st.error(
                                agent2_text or "This content is not allowed.")
                            prefilter_passed = False
                            elapsed = time.perf_counter() - time_start
                            st.caption(f"⏱️ Total time: {elapsed:.1f}s")

                        # Agent3: Not a portrait → reject
                        elif agent1_data.get("IS_PORTRAIT") is False:
                            agent3_text, _ = call_agent3_not_portrait_message(
                                API_KEY, json.dumps(agent1_data, indent=2),
                                output_language=st.session_state.output_language,
                                model=st.session_state.prefilter_model
                            )
                            st.error(
                                agent3_text or "We only provide painting lessons for portraits.")
                            prefilter_passed = False
                            elapsed = time.perf_counter() - time_start
                            st.caption(f"⏱️ Total time: {elapsed:.1f}s")

                    if not prefilter_passed:
                        pass  # Already showed error, skip evaluation
                    else:
                        # Add new iteration (without evaluation yet)
                        new_iteration = {
                            "image_base64": image_base64,
                            "image_name": uploaded_file.name,
                            "timestamp": datetime.now().isoformat(),
                            "evaluation": None
                        }
                        st.session_state.iterations.append(new_iteration)
                        iteration_added = True

                        # Determine mode
                        is_comparison = len(st.session_state.iterations) > 1

                        if is_comparison:
                            # Comparison mode
                            st.info(
                                f"📊 Comparison mode: iteration {len(st.session_state.iterations)}")
                            comparison_data = get_comparison_data(
                                st.session_state.iterations)
                            user_content = build_comparison_content(
                                comparison_data)
                            system_prompt = COMPARISON_PROMPT.format(
                                julia_style_rules=JULIA_STYLE_RULES,
                                audience_complexity=AUDIENCE_COMPLEXITY.get(
                                    st.session_state.skill_level, AUDIENCE_COMPLEXITY_BEGINNER),
                                output_language=st.session_state.output_language
                            )
                            selected_model = st.session_state.comparison_model
                        else:
                            # First evaluation
                            st.info("🎨 First portrait evaluation")
                            user_content = build_standalone_content(
                                image_base64)
                            system_prompt = EVALUATE_PORTRAIT_STANDALONE.format(
                                reference_context="",  # Empty by default, can be customized if needed
                                julia_style_rules=JULIA_STYLE_RULES,
                                audience_complexity=AUDIENCE_COMPLEXITY.get(
                                    st.session_state.skill_level, AUDIENCE_COMPLEXITY_BEGINNER),
                                output_language=st.session_state.output_language
                            )
                            selected_model = st.session_state.standalone_model

                        # API call
                        response_text, usage = call_openai_api(
                            API_KEY,
                            system_prompt,
                            user_content,
                            model=selected_model,
                            response_format={"type": "json_object"},
                        )

                        # Parse response
                        parsed_response = parse_evaluation_response(
                            response_text, is_comparison)
                        standard_eval = extract_standard_evaluation(
                            parsed_response, is_comparison)

                        # Save evaluation
                        st.session_state.iterations[-1]["evaluation"] = standard_eval
                        st.session_state.iterations[-1]["raw_response"] = response_text
                        st.session_state.iterations[-1]["parsed_response"] = parsed_response
                        st.session_state.iterations[-1]["system_prompt"] = system_prompt
                        st.session_state.iterations[-1]["model"] = selected_model

                        # Add to chat history
                        st.session_state.chat_history.append({
                            "role": "user",
                            "content": f"Uploaded: {uploaded_file.name}",
                            "image": image_base64
                        })
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": response_text,
                            "evaluation": standard_eval,
                            "is_comparison": is_comparison,
                            "parsed_response": parsed_response
                        })

                        elapsed = time.perf_counter() - time_start
                        st.success(
                            f"✅ Evaluation received! Tokens used: {usage.get('total_tokens', 'N/A')} | ⏱️ Total time: {elapsed:.1f}s")

                        # Display result
                        st.divider()
                        st.subheader(
                            f"📝 Evaluation Result (Iteration {len(st.session_state.iterations)})")
                        display_evaluation(
                            standard_eval, is_comparison, parsed_response, response_text)

                except requests.exceptions.RequestException as e:
                    if iteration_added:
                        st.session_state.iterations.pop()  # Remove failed iteration
                    st.error(f"API Error: {e}")
                except Exception as e:
                    if iteration_added:
                        st.session_state.iterations.pop()
                    st.error(f"Error: {e}")

with col_history:
    st.header("📜 Iteration History")

    if not st.session_state.iterations:
        st.info("History is empty. Upload your first portrait!")
    else:
        for i, iteration in enumerate(reversed(st.session_state.iterations)):
            idx = len(st.session_state.iterations) - i
            avg_score = calculate_average_score(iteration.get("evaluation"))

            with st.expander(f"**Iteration {idx}** - {avg_score:.1f}/10" if avg_score else f"**Iteration {idx}**", expanded=(i == 0)):
                st.caption(f"📁 {iteration.get('image_name', 'Unknown')}")
                st.caption(f"🕐 {iteration.get('timestamp', 'N/A')[:19]}")

                if iteration.get("evaluation"):
                    for cat, data in iteration["evaluation"].items():
                        if isinstance(data, dict) and "score" in data:
                            st.write(f"• {cat}: **{data['score']}**/10")

                # Raw JSON view button for each iteration
                if iteration.get("raw_response"):
                    with st.expander("📄 Raw JSON", expanded=False):
                        st.code(iteration.get("raw_response"), language="json")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #546e7a; font-size: 0.8rem;'>
    🎨 Portrait Evaluation Assistant | Powered by GPT-4o
</div>
""", unsafe_allow_html=True)
