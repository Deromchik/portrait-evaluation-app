import streamlit as st
import json
import base64
import requests
from pathlib import Path
from datetime import datetime

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

# Prompts
EVALUATE_PORTRAIT_STANDALONE = """
You are provided with an image of a student's portrait painting. Your task is to thoroughly analyze the student's painting based on several artistic criteria.

Besides positive feedback it is also important to give constructive criticism to the student.

If the student's portrait demonstrates a high level of skill with accurate proportions, anatomy, and other key elements, offer praise for these strengths and provide constructive recommendations for refinement. Focus on highlighting what works well and suggesting ways to enhance the overall impact. However, if there are clear areas for improvement (such as disproportionate features, incorrect anatomy, or lack of depth), deliver constructive criticism gently and with specificity. Critique only the aspects that truly need improvement and avoid criticizing elements that are executed well.

### DYNAMIC REFERENCE SECTION:

### CONVERSATION CONTEXT INTEGRATION:
If conversation history is provided, you MUST actively incorporate the user's specific requests, concerns, or focus areas into your analysis. For each relevant section, address the user's questions directly:

**Context-Driven Analysis Rules:**
- If user asks about specific techniques (e.g., "blending", "proportions", "colors"), provide extra detailed analysis in those sections
- If user mentions their skill level (e.g., "beginner", "first attempt"), adjust criticism level and provide appropriate guidance
- If user requests focus on particular areas, prioritize those in your feedback
- If user mentions previous feedback or improvements they tried, acknowledge and evaluate their progress
- If user asks about colors for a black-and-white image, still include Color Theory section with advice on potential color palettes
- If user expresses specific artistic goals or mood they're trying to achieve, evaluate how well the portrait accomplishes this

**Section-Specific Context Integration:**
1. **Composition**: If user mentions compositional experiments or concerns, analyze them in detail
2. **Proportions**: If user mentions proportion struggles, provide specific measurements and guidance
3. **Color Theory**: If user asks about colors (even for B&W images), provide color suggestions and theory
4. **Brushwork**: If user mentions technique struggles, focus on stroke analysis and improvement tips
5. **Expression**: If user mentions trying to capture specific emotions, evaluate emotional success
6. **Overall**: Always address the user's main questions or concerns from conversation history

If the student's portrait demonstrates a high level of skill with accurate proportions, anatomy, and other key elements, offer praise for these strengths and provide constructive recommendations for refinement. Focus on highlighting what works well and suggesting ways to enhance the overall impact. However, if there are clear areas for improvement (such as disproportionate features, incorrect anatomy, or lack of depth), deliver constructive criticism gently and with specificity. Critique only the aspects that truly need improvement and avoid criticizing elements that are executed well.

Criticism should only be applied to aspects where there is a clear and significant need for improvement.

Use the word "however" only once , always write unique phrases!

### Analysis Criteria:
Your analysis should include the following elements, each with detailed and comprehensive explanations:

1. **Composition and Design**
   - **Balance and Harmony:** Assess how well the elements of the portrait are arranged. Is there a sense of balance and harmony?
   - **Use of Space:** Evaluate the relationship between the subject and the background. Is there effective use of negative space?
   - **Focus and Emphasis:** Does the composition guide the viewer's eye and emphasize key elements, such as the face?

2. **Proportions and Anatomy**
   - **Accuracy of Proportions:** Are the facial features and overall anatomy accurate and proportionate?
   - **Understanding of Anatomy:** How well are the underlying bone structure and muscles represented?

3. **Perspective and Depth**
   - **Perspective:** Is there a clear sense of depth and consistent perspective throughout the portrait?
   - **Foreshortening:** If applicable, is foreshortening used effectively, particularly in limbs or facial features?

4. **Use of Light and Shadow (Chiaroscuro)**
   - **Light Source:** Is the light source clearly defined and consistent?
   - **Shadows and Highlights:** Are shadows and highlights used to create depth and dimension effectively?

5. **Color Theory and Application**
   - **For Color Portraits:**
     - **Color Harmony:** Evaluate the harmony of the color palette. Do the colors work well together?
     - **Skin Tones:** Are the skin tones realistic, reflecting variations due to light and shadow?
     - **Temperature:** Is there an effective use of warm and cool tones to convey depth and mood?
   - **CRITICAL: Black-and-White Portraits as Valid Artistic Style:**
     - Black-and-white (monochrome) portraits are a legitimate and respected artistic style, not an incomplete work
     - Do NOT penalize black-and-white portraits for lacking color - evaluate them based on tonal values, contrast, and grayscale mastery
     - For black-and-white portraits, evaluate:
       * **Tonal Range:** How effectively does the portrait use the full range from pure white to deep black?
       * **Contrast:** Is there appropriate contrast to create depth and visual interest?
       * **Tonal Transitions:** Are the gradations between light and dark smooth and intentional?
       * **Value Relationships:** How well do the values work together to create form and dimension?
     - Black-and-white portraits can achieve scores of 7-10 if they demonstrate excellent tonal control, contrast, and value relationships

6. **Brushwork and Technique**
   - **Brushstrokes:** Assess the control and intentionality of brushstrokes. Do they contribute to the texture and surface quality of the portrait?
   - **Surface Quality:** Consider how the surface of the painting looks up close and from a distance. Is there variation in texture that adds to the piece?

7. **Expression and Emotion**
   - **Facial Expression:** Does the portrait capture a specific mood or emotion convincingly?
   - **Character and Personality:** How well does the portrait convey the personality or essence of the subject?

8. **Creativity and Originality**
   - **Personal Style:** Is there a unique style or approach evident in the portrait?
   - **Conceptual Depth:** Does the portrait offer something thought-provoking or original beyond technical execution?

9. **Attention to Detail**
   - **Detailing:** How well are fine details such as skin texture, reflections, or hair handled?
   - **Completeness:** Is the portrait carefully finished, or are there areas that seem incomplete or rushed?

10. **Overall Impact**
   - **Emotional Response:** What emotional response does the portrait evoke in the viewer?
   - **Cohesiveness:** Do all the elements work together to create a strong and unified work?

### Important Rules:
1. Provide clear, constructive feedback, highlighting both strengths and areas for improvement.
2. Avoid overly technical language; aim to be accessible and encouraging.
3. Reference specific aspects of the painting to support your evaluation.
4. **CRITICAL:** For each category, provide a numerical score from 1-10 where:
   - 1-3: Significant improvement needed
   - 4-6: Basic level, noticeable areas for improvement
   - 7-8: Good work with minor areas to refine
   - 9-10: Excellent, professional level work

### Advanced Feedback Requirements:
- More detailed and deeper analysis that goes beyond the standard feedback
- Specific areas for improvement with precise locations and technical details
- Advanced insights about artistic techniques, composition strategies, or technical refinements
- Actionable recommendations with specific steps the student can take
- CRITICAL: The advanced_feedback MUST NOT repeat information already stated in the regular "feedback" field
- Advanced_feedback should be 200-350 tokens in length
- Focus on providing unique, additional value that complements but does not duplicate the standard feedback

### Output Format:
Your answer should be purely JSON, without any additional explanation such as "```json", for example. 

{{
    "Composition and Design": {{
        "score": <number 1-10>,
        "feedback": "<Comprehensive and Detailed String>",
        "advanced_feedback": "<More detailed and deeper analysis (200-350 tokens), focusing on specific areas for improvement, advanced insights, and actionable recommendations. Must NOT repeat information from feedback field.>"
    }},
    "Proportions and Anatomy": {{
        "score": <number 1-10>,
        "feedback": "<Comprehensive and Detailed String>",
        "advanced_feedback": "<More detailed and deeper analysis (200-350 tokens), focusing on specific areas for improvement, advanced insights, and actionable recommendations. Must NOT repeat information from feedback field.>"
    }},
    "Perspective and Depth": {{
        "score": <number 1-10>,
        "feedback": "<Comprehensive and Detailed String>",
        "advanced_feedback": "<More detailed and deeper analysis (200-350 tokens), focusing on specific areas for improvement, advanced insights, and actionable recommendations. Must NOT repeat information from feedback field.>"
    }},
    "Use of Light and Shadow": {{
        "score": <number 1-10>,
        "feedback": "<Comprehensive and Detailed String>",
        "advanced_feedback": "<More detailed and deeper analysis (200-350 tokens), focusing on specific areas for improvement, advanced insights, and actionable recommendations. Must NOT repeat information from feedback field.>"
    }},
    "Color Theory and Application": {{
        "score": <number 1-10>,
        "feedback": "<Comprehensive and Detailed String>",
        "advanced_feedback": "<More detailed and deeper analysis (200-350 tokens), focusing on specific areas for improvement, advanced insights, and actionable recommendations. Must NOT repeat information from feedback field.>"
    }},
    "Brushwork and Technique": {{
        "score": <number 1-10>,
        "feedback": "<Comprehensive and Detailed String>",
        "advanced_feedback": "<More detailed and deeper analysis (200-350 tokens), focusing on specific areas for improvement, advanced insights, and actionable recommendations. Must NOT repeat information from feedback field.>"
    }},
    "Expression and Emotion": {{
        "score": <number 1-10>,
        "feedback": "<Comprehensive and Detailed String>",
        "advanced_feedback": "<More detailed and deeper analysis (200-350 tokens), focusing on specific areas for improvement, advanced insights, and actionable recommendations. Must NOT repeat information from feedback field.>"
    }},
    "Creativity and Originality": {{
        "score": <number 1-10>,
        "feedback": "<Comprehensive and Detailed String>",
        "advanced_feedback": "<More detailed and deeper analysis (200-350 tokens), focusing on specific areas for improvement, advanced insights, and actionable recommendations. Must NOT repeat information from feedback field.>"
    }},
    "Attention to Detail": {{
        "score": <number 1-10>,
        "feedback": "<Comprehensive and Detailed String>",
        "advanced_feedback": "<More detailed and deeper analysis (200-350 tokens), focusing on specific areas for improvement, advanced insights, and actionable recommendations. Must NOT repeat information from feedback field.>"
    }},
    "Overall Impact": {{
        "score": <number 1-10>,
        "feedback": "<Comprehensive and Detailed String>",
        "advanced_feedback": "<More detailed and deeper analysis (200-350 tokens), focusing on specific areas for improvement, advanced insights, and actionable recommendations. Must NOT repeat information from feedback field.>"
    }}
}}

### Input:
You will be provided with one image: the student's portrait painting.

### Output Example:
{{
    "Composition and Design": {{
        "score": 7,
        "feedback": "I feel that your composition is quite balanced, with the subject centered in a way that feels natural. However, I think you could push the boundaries a bit by experimenting with a less conventional placement. While the use of negative space gives breathing room, it might feel a little too safe—perhaps trying something more dynamic with the positioning of elements could create a stronger impact.",
        "advanced_feedback": "Consider applying the rule of thirds more dynamically by positioning the subject's eye line at the upper third intersection point rather than center. The current negative space, while balanced, could be leveraged more strategically—the left side could benefit from subtle visual weight through a gradient or texture variation. Analyze how masters like Vermeer use off-center placement to create visual tension. The background's uniform treatment doesn't guide the eye effectively; introducing a subtle value gradient from top-left to bottom-right would create depth. Experiment with cropping variations: try a tighter frame focusing on the eyes and upper face, or a wider format emphasizing the relationship between figure and environment. The current composition reads as safe rather than intentional—push toward either extreme symmetry or deliberate asymmetry."
    }},
    "Proportions and Anatomy": {{
        "score": 6,
        "feedback": "You've done a solid job with the facial proportions, particularly in how you've captured the jawline and cheekbones. The nose appears slightly elongated - focusing on the relationship between nose width and length could help create more balanced proportions. Studying facial anatomy references and practicing quick proportion sketches would strengthen the overall anatomy and make the portrait more harmonious.",
        "advanced_feedback": "The nose-to-face width ratio is approximately 1:5, but the current rendering suggests 1:4.5, creating subtle elongation. Measure the distance from the inner eye corners—this should equal the nose width at the nostrils. The philtrum (area between nose and upper lip) appears compressed; it should be roughly one-third the nose length. The zygomatic arch (cheekbone) placement is accurate, but the masseter muscle definition below it needs refinement—add a subtle shadow plane where the jaw angles inward. The temporal bone area (temple) lacks the subtle concavity that creates realistic skull structure. Practice Loomis head construction: divide the head into thirds vertically (hairline to brow, brow to nose base, nose base to chin) and verify your measurements match these proportions. The ear placement is slightly forward—it should align with the brow line at the top and nose base at the bottom."
    }},
    "Perspective and Depth": {{
        "score": 7,
        "feedback": "I can see you've worked carefully to maintain perspective, and it's working well for the most part. The slight foreshortening on the nose is nicely done. However, I feel the background could use a bit more depth to enhance the overall spatial relationship between the subject and its surroundings. Adding more complexity here would heighten the sense of realism.",
        "advanced_feedback": "The atmospheric perspective in the background needs more pronounced value shift—objects further away should be lighter and less saturated. Currently, the background maintains similar contrast to the foreground subject. Apply aerial perspective principles: reduce contrast by 30-40% in distant areas, shift toward cooler tones (if working in color), and soften edges. The foreground-to-background transition lacks a clear midground element—introduce a subtle intermediate plane (perhaps a blurred edge or soft form) to create three distinct spatial zones. The nose foreshortening is effective, but the ears need corresponding perspective adjustment—they should appear slightly smaller and positioned further back due to the three-quarter view. Study how Sargent handles background simplification: he maintains detail in the face while allowing background elements to dissolve into suggestive forms."
    }}
}}

### Important:
- Ensure that each part of the analysis is detailed and specific, providing rich information that can be used in further evaluations.
- **CRITICAL:** Always provide numerical scores (1-10) for each category based on your professional assessment of the artwork.
- **CONVERSATION INTEGRATION:** Always address specific user requests or concerns mentioned in conversation history within the relevant sections.
- **NO TEACHER REFERENCES:** Never mention teacher, teacher's reference, or teacher comparisons since this agent evaluates standalone portraits.
"""

COMPARISON_PROMPT = """
You are an expert art instructor analyzing a student's portrait painting progress across multiple iterations.

You will receive:
1. **FIRST ITERATION**: The student's initial portrait and its expert evaluation
2. **PREVIOUS ITERATION**: The most recent portrait before the current one, with its expert evaluation
3. **CURRENT ITERATION**: The student's latest portrait (to be evaluated)

Your task is to:
1. Analyze the OVERALL PROGRESS from the first iteration to the current one
2. Compare the CURRENT portrait specifically against the PREVIOUS iteration
3. Provide a NEW evaluation for the current portrait using the same criteria as previous evaluations

Besides positive feedback it is also important to give constructive criticism to the student.

### OUTPUT STYLE (VERY IMPORTANT):
- The reader is a 12-14 year old girl. Use simple words and short sentences.
- Write in Julia's friendly, encouraging style (warm, supportive, practical tips).
- Avoid complex art jargon. If you must mention a technique, explain it in simple words.
- Every feedback text MUST include 1-3 emoji characters, placed naturally inside the text (not all at the very end).
- Do NOT add an emoji-only tail. Do not put more than 1 emoji in a row.
- Keep each category's feedback brief: 1-2 short sentences max.
- Keep `progress_summary` texts short and friendly too (also include emojis).
- **CRITICAL:** The "advanced_feedback" field MUST also use simple words suitable for a 12-14 year old girl. Even though it contains more detailed analysis, it must be written in the same accessible, child-friendly language as the regular feedback. Never use complex terminology without explaining it in simple words.

If the student's portrait demonstrates a high level of skill with accurate proportions, anatomy, and other key elements, offer praise for these strengths and provide constructive recommendations for refinement. Focus on highlighting what works well and suggesting ways to enhance the overall impact. However, if there are clear areas for improvement (such as disproportionate features, incorrect anatomy, or lack of depth), deliver constructive criticism gently and with specificity. Critique only the aspects that truly need improvement and avoid criticizing elements that are executed well.

Criticism should only be applied to aspects where there is a clear and significant need for improvement.

Use the word "however" only once , always write unique phrases!

## CRITICAL: OBJECTIVE FIRST ITERATION ASSESSMENT

When evaluating progress, you MUST objectively assess what the FIRST iteration actually was:

### Recognizing Basic Sketches (First Iteration):
A basic sketch typically has:
- Visible construction/guide lines (cross lines on face, proportion markers)
- Minimal detail in hair (simple lines vs. textured strands)
- Schematic facial features (basic shapes vs. refined expressions)
- No shading or minimal tonal work
- Placeholder-style elements

**If the first iteration is a basic sketch:**
- first_score values should typically be in the 4-6 range, NOT 7-9
- A rough sketch with construction lines is NOT "good proportions" (7-8) - it's "basic foundation" (4-5)
- Simple hair lines are NOT "good attention to detail" (7-8) - they are "foundational work" (4-5)

### Recognizing Dramatic Progress:
If comparing a basic sketch (iteration 1) to a refined portrait (current iteration):
- Use language like "DRAMATICALLY improved", "significant transformation", "remarkable progress"
- Do NOT say "maintained" or "unchanged" when there's obvious visual transformation
- Score differences should reflect the actual visual difference (e.g., from 5 to 8, not 8 to 8)

### Progress Language Guide:
| Visual Change | Correct Language | Score Change |
|---|---|---|
| Basic sketch → Refined work | "dramatically improved", "transformed" | +3 to +4 |
| Noticeable improvement | "noticeably improved", "refined" | +1 to +2 |
| Minor refinement | "slightly improved", "subtle refinement" | +1 |
| No visible change | "maintained", "unchanged" | 0 |
| Quality declined | "regressed", "declined" | -1 to -3 |

## COMPARISON ANALYSIS RULES:

### 1. Long-term Progress Analysis (First → Current):
- Identify major improvements achieved since the beginning
- Highlight the student's growth trajectory
- Note which initial weaknesses have been addressed
- Calculate overall score improvement

### 2. Short-term Progress Analysis (Previous → Current):
- Identify SPECIFIC visual differences between previous and current portraits
- Note which elements have been modified, added, or refined
- Assess whether changes align with previous feedback suggestions
- Distinguish between "requested improvements" and "self-initiated improvements"
- **IMPORTANT:** The current iteration may show LESS progress or even REGRESSION compared to previous iterations. Be honest about this.

### 3. Score Progression:
- Reference BOTH the first iteration score AND the previous iteration score for each category
- Justify score changes with visual evidence
- Be generous with score increases when genuine improvement is visible
- **CRITICAL:** Scores CAN and SHOULD decrease if quality has objectively declined or if the current work is weaker than previous iterations
- Do NOT assume progress is always positive - evaluate each iteration objectively on its own merits

### 4. Feedback-Score Consistency (MANDATORY):
- **Your feedback text MUST match your numerical score change**
- If you write "noticeable improvement" or "refinement visible" → score MUST increase (e.g., +1 or +2)
- If you write "unchanged" or "maintained" → score stays the same
- If you write "regression" or "decline" or "less refined" → score MUST decrease
- **NEVER** describe improvement in feedback while marking score as "unchanged" - this is a contradiction
- **NEVER** describe problems in feedback while increasing the score
- Before finalizing, verify: Does my feedback language match my score change?

### 5. Honest Assessment:
- If the current portrait is objectively WORSE than the previous one, say so clearly and lower the score
- Do not inflate scores to avoid hurting feelings - honest feedback helps the student improve
- If there are no visible changes, be specific about what remains unchanged
- If changes made the work worse, explain why and how to fix it

### 6. Feedback Integration:
- Acknowledge specific improvements that address previous suggestions
- Highlight what the student did well in their revision
- Provide NEW suggestions for remaining areas of improvement
- Avoid repeating criticism for issues that have been resolved

### 7. Progress Recognition:
- **CELEBRATE DRAMATIC IMPROVEMENTS**: If a basic sketch transformed into a refined portrait, explicitly acknowledge this transformation
- When progress is significant, use enthusiastic language: "remarkable transformation", "impressive growth", "substantial improvement"
- Recognize effort and dedication to improvement
- Motivate continued practice with specific next steps
- Be honest when effort did not result in improvement
- **IMPORTANT**: Do not downplay significant progress by using neutral language like "maintained" when dramatic change occurred

## ANALYSIS CRITERIA:
Your analysis should include the following elements, each with detailed and comprehensive explanations:

1. **Composition and Design**
   - **Balance and Harmony:** Assess how well the elements of the portrait are arranged. Is there a sense of balance and harmony?
   - **Use of Space:** Evaluate the relationship between the subject and the background. Is there effective use of negative space?
   - **Focus and Emphasis:** Does the composition guide the viewer's eye and emphasize key elements, such as the face?

2. **Proportions and Anatomy**
   - **Accuracy of Proportions:** Are the facial features and overall anatomy accurate and proportionate?
   - **Understanding of Anatomy:** How well are the underlying bone structure and muscles represented?

3. **Perspective and Depth**
   - **Perspective:** Is there a clear sense of depth and consistent perspective throughout the portrait?
   - **Foreshortening:** If applicable, is foreshortening used effectively, particularly in limbs or facial features?

4. **Use of Light and Shadow (Chiaroscuro)**
   - **Light Source:** Is the light source clearly defined and consistent?
   - **Shadows and Highlights:** Are shadows and highlights used to create depth and dimension effectively?

5. **Color Theory and Application**
   - **For Color Portraits:**
     - **Color Harmony:** Evaluate the harmony of the color palette. Do the colors work well together?
     - **Skin Tones:** Are the skin tones realistic, reflecting variations due to light and shadow?
     - **Temperature:** Is there an effective use of warm and cool tones to convey depth and mood?
   - **CRITICAL: Black-and-White Portraits as Valid Artistic Style:**
     - Black-and-white (monochrome) portraits are a legitimate and respected artistic style, not an incomplete work
     - Do NOT penalize black-and-white portraits for lacking color - evaluate them based on tonal values, contrast, and grayscale mastery
     - For black-and-white portraits, evaluate:
       * **Tonal Range:** How effectively does the portrait use the full range from pure white to deep black?
       * **Contrast:** Is there appropriate contrast to create depth and visual interest?
       * **Tonal Transitions:** Are the gradations between light and dark smooth and intentional?
       * **Value Relationships:** How well do the values work together to create form and dimension?
     - Black-and-white portraits can achieve scores of 7-10 if they demonstrate excellent tonal control, contrast, and value relationships

6. **Brushwork and Technique**
   - **Brushstrokes:** Assess the control and intentionality of brushstrokes. Do they contribute to the texture and surface quality of the portrait?
   - **Surface Quality:** Consider how the surface of the painting looks up close and from a distance. Is there variation in texture that adds to the piece?

7. **Expression and Emotion**
   - **Facial Expression:** Does the portrait capture a specific mood or emotion convincingly?
   - **Character and Personality:** How well does the portrait convey the personality or essence of the subject?

8. **Creativity and Originality**
   - **Personal Style:** Is there a unique style or approach evident in the portrait?
   - **Conceptual Depth:** Does the portrait offer something thought-provoking or original beyond technical execution?

9. **Attention to Detail**
   - **Detailing:** How well are fine details such as skin texture, reflections, or hair handled?
   - **Completeness:** Is the portrait carefully finished, or are there areas that seem incomplete or rushed?

10. **Overall Impact**
    - **Emotional Response:** What emotional response does the portrait evoke in the viewer?
    - **Cohesiveness:** Do all the elements work together to create a strong and unified work?

## IMPORTANT RULES:
1. Provide clear, constructive feedback, highlighting both strengths and areas for improvement.
2. Avoid overly technical language; aim to be accessible and encouraging.
3. Reference specific aspects of the painting to support your evaluation.
4. **CRITICAL:** For each category, provide a numerical score from 1-10 where:
   - 1-3: Significant improvement needed
   - 4-6: Basic level, noticeable areas for improvement
   - 7-8: Good work with minor areas to refine
   - 9-10: Excellent, professional level work
5. **NO TEACHER REFERENCES:** Never mention teacher, teacher's reference, or teacher comparisons.

### Advanced Feedback Requirements:
- **CRITICAL LANGUAGE REQUIREMENT:** Advanced_feedback MUST be written in simple words suitable for a 12-14 year old girl. Use the same simple, accessible language as the regular feedback field. Avoid complex art terminology, technical jargon, or sophisticated vocabulary. If you must mention a technique, explain it in simple, everyday words that a child would understand.
- The advanced_feedback MUST NOT repeat information already stated in the regular "feedback" field
- Detailed comparison with the previous iteration: Explain what specifically changed compared to the previous portrait, how it compares to what was there before, and whether the change is good, mediocre, or needs further work. Use simple words to describe these changes.
- More detailed and deeper analysis that goes beyond the standard feedback, but expressed in simple, child-friendly language
- Specific areas for improvement with precise locations and technical details, explained in simple terms
- Advanced insights about artistic techniques, composition strategies, or technical refinements, but explained as if talking to a child
- Actionable recommendations with specific steps the student can take, using simple, clear instructions
- Advanced_feedback should be 200-350 tokens in length
- **CRITICAL:** For advanced_feedback, always include a comparison section explaining what changed from the previous iteration, how it compares to the previous version, and an assessment of whether the change is successful or needs refinement - all in simple words
- Focus on providing unique, additional value that complements but does not duplicate the standard feedback
- Remember: Even though advanced_feedback is more detailed, it must still be understandable to a 12-14 year old. Break down complex concepts into simple explanations.

## OUTPUT FORMAT:
Your answer should be purely JSON, without any additional explanation such as "```json", for example. 

{{
    "progress_summary": {{
        "overall_improvement": "<Summary of growth from first to current iteration>",
        "recent_changes": "<Specific changes from previous to current iteration>",
        "self_initiated_improvements": "<Changes made by student's own initiative, not from feedback>"
    }},
    "Composition and Design": {{
        "first_score": <number>,
        "previous_score": <number>,
        "current_score": <number 1-10>,
        "score_change": "<+X/-X/unchanged from previous>",
        "feedback": "<Comprehensive and Detailed feedback acknowledging progress and suggesting improvements>",
        "advanced_feedback": "<More detailed analysis (200-350 tokens) comparing current to previous iteration, explaining what changed, how it compares, and whether the change is successful. Must include specific improvement areas and advanced insights. Must NOT repeat information from feedback field.>"
    }},
    "Proportions and Anatomy": {{
        "first_score": <number>,
        "previous_score": <number>,
        "current_score": <number 1-10>,
        "score_change": "<+X/-X/unchanged from previous>",
        "feedback": "<Comprehensive and Detailed feedback>",
        "advanced_feedback": "<More detailed analysis (200-350 tokens) comparing current to previous iteration, explaining what changed, how it compares, and whether the change is successful. Must include specific improvement areas and advanced insights. Must NOT repeat information from feedback field.>"
    }},
    "Perspective and Depth": {{
        "first_score": <number>,
        "previous_score": <number>,
        "current_score": <number 1-10>,
        "score_change": "<+X/-X/unchanged from previous>",
        "feedback": "<Comprehensive and Detailed feedback>",
        "advanced_feedback": "<More detailed analysis (200-350 tokens) comparing current to previous iteration, explaining what changed, how it compares, and whether the change is successful. Must include specific improvement areas and advanced insights. Must NOT repeat information from feedback field.>"
    }},
    "Use of Light and Shadow": {{
        "first_score": <number>,
        "previous_score": <number>,
        "current_score": <number 1-10>,
        "score_change": "<+X/-X/unchanged from previous>",
        "feedback": "<Comprehensive and Detailed feedback>",
        "advanced_feedback": "<More detailed analysis (200-350 tokens) comparing current to previous iteration, explaining what changed, how it compares, and whether the change is successful. Must include specific improvement areas and advanced insights. Must NOT repeat information from feedback field.>"
    }},
    "Color Theory and Application": {{
        "first_score": <number>,
        "previous_score": <number>,
        "current_score": <number 1-10>,
        "score_change": "<+X/-X/unchanged from previous>",
        "feedback": "<Comprehensive and Detailed feedback>",
        "advanced_feedback": "<More detailed analysis (200-350 tokens) comparing current to previous iteration, explaining what changed, how it compares, and whether the change is successful. Must include specific improvement areas and advanced insights. Must NOT repeat information from feedback field.>"
    }},
    "Brushwork and Technique": {{
        "first_score": <number>,
        "previous_score": <number>,
        "current_score": <number 1-10>,
        "score_change": "<+X/-X/unchanged from previous>",
        "feedback": "<Comprehensive and Detailed feedback>",
        "advanced_feedback": "<More detailed analysis (200-350 tokens) comparing current to previous iteration, explaining what changed, how it compares, and whether the change is successful. Must include specific improvement areas and advanced insights. Must NOT repeat information from feedback field.>"
    }},
    "Expression and Emotion": {{
        "first_score": <number>,
        "previous_score": <number>,
        "current_score": <number 1-10>,
        "score_change": "<+X/-X/unchanged from previous>",
        "feedback": "<Comprehensive and Detailed feedback>",
        "advanced_feedback": "<More detailed analysis (200-350 tokens) comparing current to previous iteration, explaining what changed, how it compares, and whether the change is successful. Must include specific improvement areas and advanced insights. Must NOT repeat information from feedback field.>"
    }},
    "Creativity and Originality": {{
        "first_score": <number>,
        "previous_score": <number>,
        "current_score": <number 1-10>,
        "score_change": "<+X/-X/unchanged from previous>",
        "feedback": "<Comprehensive and Detailed feedback>",
        "advanced_feedback": "<More detailed analysis (200-350 tokens) comparing current to previous iteration, explaining what changed, how it compares, and whether the change is successful. Must include specific improvement areas and advanced insights. Must NOT repeat information from feedback field.>"
    }},
    "Attention to Detail": {{
        "first_score": <number>,
        "previous_score": <number>,
        "current_score": <number 1-10>,
        "score_change": "<+X/-X/unchanged from previous>",
        "feedback": "<Comprehensive and Detailed feedback>",
        "advanced_feedback": "<More detailed analysis (200-350 tokens) comparing current to previous iteration, explaining what changed, how it compares, and whether the change is successful. Must include specific improvement areas and advanced insights. Must NOT repeat information from feedback field.>"
    }},
    "Overall Impact": {{
        "first_score": <number>,
        "previous_score": <number>,
        "current_score": <number 1-10>,
        "score_change": "<+X/-X/unchanged from previous>",
        "feedback": "<Comprehensive and Detailed feedback>",
        "advanced_feedback": "<More detailed analysis (200-350 tokens) comparing current to previous iteration, explaining what changed, how it compares, and whether the change is successful. Must include specific improvement areas and advanced insights. Must NOT repeat information from feedback field.>"
    }}
}}

## FINAL VERIFICATION CHECKLIST (Complete before submitting):

Before finalizing your response, verify each of these points:

1. **First Iteration Reality Check:**
   - Look at the FIRST image again. Is it a basic sketch with construction lines?
   - If YES: Are my first_score values in the 4-6 range? (NOT 7-9)
   - Did I inflate first_score because I saw the later refined versions?

2. **Progress Magnitude Check:**
   - Is there a DRAMATIC visual difference between first and current iteration?
   - If YES: Does my progress_summary use words like "dramatically improved", "transformed", "remarkable progress"?
   - If YES: Are my score differences at least +2 to +4 points (not just +1)?

3. **Language-Score Consistency:**
   - For EACH category: Does my feedback text match my numerical score change?
   - If I wrote "improved" → Did the score increase?
   - If I wrote "maintained" → Is the score truly unchanged AND do the images look identical?
   - If I wrote "declined" → Did the score decrease?

4. **Avoid "Maintained" Trap:**
   - Am I using "maintained" or "unchanged" when there's clearly visible improvement?
   - If first iteration was a sketch and current is refined → I should NOT say "maintained good proportions"
   - Instead say: "proportions have dramatically improved from the initial sketch"

5. **Honest Assessment:**
   - Would a human art instructor agree with my scores?
   - Am I being fair to the student's actual progress?

6. **Advanced Feedback Language Check:**
   - Is my advanced_feedback written in simple words that a 12-14 year old girl would understand?
   - Have I avoided complex art terminology or explained it in simple words?
   - Does advanced_feedback use the same accessible, child-friendly language as the regular feedback?
   - Would a child be able to understand all the concepts I've explained in advanced_feedback?

7. **Advanced Feedback Uniqueness Check:**
   - Does my advanced_feedback contain any information that repeats what's already in the feedback field?
   - Have I ensured zero overlap between feedback and advanced_feedback content?
   - Is advanced_feedback providing completely new insights or different perspectives?

**OUTPUT LANGUAGE:** All feedback text, progress_summary, and advanced_feedback must be written in {output_language}.
"""

# Initialize session state
if "iterations" not in st.session_state:
    st.session_state.iterations = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "output_language" not in st.session_state:
    st.session_state.output_language = "English"


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


def call_openai_api(api_key, system_prompt, user_content):
    """Call OpenAI API"""
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

    data = {
        "model": "gpt-4o",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 6000
    }

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
            "raw_response": iteration.get("raw_response")
        }
        export_list.append(export_item)
    return export_list


def get_full_logs(iterations):
    """Prepares complete API logs for export (without base64 images)"""
    logs = {
        "export_timestamp": datetime.now().isoformat(),
        "total_iterations": len(iterations),
        "prompts": {
            "EVALUATE_PORTRAIT_STANDALONE": EVALUATE_PORTRAIT_STANDALONE,
            "COMPARISON_PROMPT": COMPARISON_PROMPT
        },
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

        iteration_log = {
            "iteration_number": i + 1,
            "timestamp": iteration.get("timestamp", "N/A"),
            "image_name": iteration.get("image_name", "Unknown"),
            "mode": "comparison" if is_comparison else "standalone",
            "api_input": {
                "model": "gpt-4o",
                "temperature": 0.1,
                "max_tokens": 6000,
                "system_prompt": "COMPARISON_PROMPT" if is_comparison else "EVALUATE_PORTRAIT_STANDALONE",
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
            with st.spinner("Analyzing portrait..."):
                try:
                    # Encode image
                    image_base64 = encode_image_to_base64(uploaded_file)

                    # Add new iteration (without evaluation yet)
                    new_iteration = {
                        "image_base64": image_base64,
                        "image_name": uploaded_file.name,
                        "timestamp": datetime.now().isoformat(),
                        "evaluation": None
                    }
                    st.session_state.iterations.append(new_iteration)

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
                            output_language=st.session_state.output_language
                        )
                    else:
                        # First evaluation
                        st.info("🎨 First portrait evaluation")
                        user_content = build_standalone_content(
                            image_base64)
                        system_prompt = EVALUATE_PORTRAIT_STANDALONE

                    # API call
                    response_text, usage = call_openai_api(
                        API_KEY,
                        system_prompt,
                        user_content
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

                    st.success(
                        f"✅ Evaluation received! Tokens used: {usage.get('total_tokens', 'N/A')}")

                    # Display result
                    st.divider()
                    st.subheader(
                        f"📝 Evaluation Result (Iteration {len(st.session_state.iterations)})")
                    display_evaluation(
                        standard_eval, is_comparison, parsed_response, response_text)

                except requests.exceptions.RequestException as e:
                    st.session_state.iterations.pop()  # Remove failed iteration
                    st.error(f"API Error: {e}")
                except Exception as e:
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