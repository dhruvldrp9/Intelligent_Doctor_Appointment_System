# Initialize LLM here
from openai import OpenAI
import time
import os


class GPTConversationSystem:
    def __init__(self):
        """Initialize the conversation system with required models and settings."""
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Initialize Whisper for STT
        # print("Loading Speech-to-Text model...")
        # self.stt_model = whisper.load_model("small", device="cpu")
        
        # # Initialize TTS
        # print("Loading Text-to-Speech model...")
        # self.tts_model = VitsModel.from_pretrained("facebook/mms-tts-eng")
        # self.tts_tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-eng")
        
        # # Audio recording settings
        # self.samplerate = 44100
        # self.channels = 1
        
        # Conversation history with carefully crafted system prompt
        self.conversation_history = [
            {
                "role": "system",
                "content": """You are an advanced AI assistant engaging in a natural spoken conversation. Your key characteristics are:

                    1. Conversational Style:
                    - Speak naturally and warmly, as if in a face-to-face conversation
                    - Use a friendly, engaging tone while maintaining professionalism
                    - Keep responses concise (2-3 sentences) as they will be spoken aloud
                    - Include appropriate conversational fillers and acknowledgments

                    2. Response Structure:
                    - Directly address the user's input
                    - Stay focused on the current topic
                    - Use natural transitions between topics
                    - Include occasional thoughtful questions to maintain engagement

                    3. Personality Traits:
                    - Show genuine interest in the conversation
                    - Express empathy and understanding
                    - Be knowledgeable but humble
                    - Maintain consistency in personality

                    4. Guidelines:
                    - Avoid overly formal language or technical jargon
                    - Don't repeat the user's words verbatim
                    - Keep responses informative but brief
                    - Express opinions when appropriate while respecting different viewpoints"""
            }
        ]
        
        # # Track conversation duration for context management
        self.conversation_start = time.time()
        self.last_context_refresh = time.time()
        self.context_refresh_interval = 600  # Refresh context every 10 minutes
        
        # # Create audio directory if it doesn't exist
        # self.audio_dir = "audio_recordings"
        # os.makedirs(self.audio_dir, exist_ok=True)

    def get_gpt_response(self, user_input: str) -> str:
        """Get response from GPT model"""
        try:
            # Check if we need to refresh context
            current_time = time.time()
            if current_time - self.last_context_refresh > self.context_refresh_interval:
                # Keep system prompt and last 2 exchanges for continuity
                self.conversation_history = [
                    self.conversation_history[0],  # System prompt
                    *self.conversation_history[-4:]  # Last 2 exchanges
                ]
                self.last_context_refresh = current_time
            
            # Add user message to conversation
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Get response from GPT
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=100,
                top_p=0.9,
                frequency_penalty=0.5,
                presence_penalty=0.5
            )
            
            # Extract the response text correctly
            assistant_response = response.choices[0].message.content.strip()
            
            # Add assistant's response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_response
            })
            
            return assistant_response
            
        except Exception as e:
            print(f"Error getting GPT response: {str(e)}")
            return "I apologize, but I encountered an error. Could you please repeat that?"
        

