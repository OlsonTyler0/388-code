# ╔═══════════════════════════════════════════════════════════╗
#   sentiment_analyzer.py
#       This is the sentiment handler. It will handle any query
#       to the natural language APi to get back good or bad 
#       scores
# ╚═══════════════════════════════════════════════════════════╝

import logging

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        try:
            from google.cloud import language_v1
            self.client = language_v1.LanguageServiceClient()
            self.language_v1 = language_v1
        except Exception as e:
            logger.error(f"Error initializing Google Cloud Natural Language API: {str(e)}")
            raise e

    def analyze_text(self, text):
        """
        Analyze the sentiment of a text using Google Cloud Natural Language API.

        Args:
            text: The text to analyze

        Returns:
            Dictionary with sentiment score, magnitude, and category
        """
        try:
            document = self.language_v1.Document(
                content=text,
                type_=self.language_v1.Document.Type.PLAIN_TEXT
            )

            sentiment = self.client.analyze_sentiment(
                request={"document": document}
            ).document_sentiment

            score = sentiment.score
            magnitude = sentiment.magnitude

            if score > 0.25:
                category = "positive"
            elif score < -0.25:
                category = "negative"
            else:
                category = "neutral"

            return {
                "score": score,
                "magnitude": magnitude,
                "category": category
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "score": 0,
                "magnitude": 0,
                "category": "neutral",
                "error": str(e)
            }

class LocalSentimentAnalyzer:
    def __init__(self):
        try:
            from textblob import TextBlob
            self.TextBlob = TextBlob
        except ImportError:
            logger.warning("TextBlob is not installed. Please install it to use local sentiment analysis.")

    def analyze_text(self, text):
        """
        Analyze the sentiment of a text using TextBlob.

        Args:
            text: The text to analyze

        Returns:
            Dictionary with sentiment score, magnitude, and category
        """
        try:
            from textblob import TextBlob
            blob = TextBlob(text)

            score = blob.sentiment.polarity

            if score > 0.2:
                category = "positive"
            elif score < -0.2:
                category = "negative"
            else:
                category = "neutral"

            magnitude = blob.sentiment.subjectivity

            return {
                "score": score,
                "magnitude": magnitude,
                "category": category
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment locally: {str(e)}")
            return {
                "score": 0,
                "magnitude": 0,
                "category": "neutral",
                "error": str(e)
            }