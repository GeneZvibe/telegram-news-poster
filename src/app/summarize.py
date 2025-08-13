"""Text summarization module for Telegram News Poster.

Implements rule-based extractive summarization with heuristics.
"""

import re
from typing import List, Dict
from .config import settings

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken if available, otherwise estimate.
    
    Args:
        text: Input text
        
    Returns:
        Token count
    """
    if TIKTOKEN_AVAILABLE:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            # Fallback to word count estimation
            pass
    
    # Simple estimation: ~4 characters per token
    return len(text) // 4


def extract_sentences(text: str) -> List[str]:
    """Extract sentences from text using simple heuristics.
    
    Args:
        text: Input text
        
    Returns:
        List of sentences
    """
    if not text:
        return []
        
    # Clean text
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Split on sentence boundaries
    sentence_endings = r'[.!?]+\s+'
    sentences = re.split(sentence_endings, text)
    
    # Clean and filter sentences
    clean_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 20 and len(sentence.split()) > 3:  # Minimum length filters
            clean_sentences.append(sentence)
            
    return clean_sentences


def score_sentence(sentence: str, keywords: List[str], position: int, total_sentences: int) -> float:
    """Score a sentence for relevance using multiple heuristics.
    
    Args:
        sentence: Sentence to score
        keywords: List of keywords to match
        position: Position of sentence in text (0-based)
        total_sentences: Total number of sentences
        
    Returns:
        Relevance score
    """
    score = 0.0
    sentence_lower = sentence.lower()
    
    # Keyword matching (weighted)
    keyword_score = 0
    for keyword in keywords:
        if keyword.lower() in sentence_lower:
            keyword_score += 2.0  # Base keyword match
            
    score += min(keyword_score, 5.0)  # Cap keyword score
    
    # Position scoring (first and last sentences often important)
    if position == 0:  # First sentence
        score += 1.5
    elif position == total_sentences - 1 and total_sentences > 1:  # Last sentence
        score += 0.5
    elif position < 3:  # Early sentences
        score += 1.0
        
    # Length scoring (prefer medium-length sentences)
    word_count = len(sentence.split())
    if 10 <= word_count <= 25:
        score += 1.0
    elif 5 <= word_count <= 35:
        score += 0.5
        
    # Sentence quality indicators
    if any(phrase in sentence_lower for phrase in 
           ['according to', 'researchers found', 'study shows', 'announced', 'revealed']):
        score += 1.0
        
    # Penalize questions and quotes
    if sentence.count('?') > 0:
        score -= 0.5
    if sentence.count('"') > 2:
        score -= 0.3
        
    # Penalize very short or very long sentences
    if word_count < 5:
        score -= 1.0
    elif word_count > 40:
        score -= 0.5
        
    return max(score, 0.0)


def create_summary(text: str, max_tokens: int = None, max_sentences: int = 3) -> str:
    """Create extractive summary using rule-based approach.
    
    Args:
        text: Input text to summarize
        max_tokens: Maximum tokens in summary (uses settings default if None)
        max_sentences: Maximum sentences in summary
        
    Returns:
        Generated summary
    """
    if not text:
        return ""
        
    if max_tokens is None:
        max_tokens = settings.max_summary_tokens
        
    # Extract sentences
    sentences = extract_sentences(text)
    
    if not sentences:
        return text[:200] + "..." if len(text) > 200 else text
        
    # If only one sentence, return it (possibly truncated)
    if len(sentences) == 1:
        sentence = sentences[0]
        if count_tokens(sentence) <= max_tokens:
            return sentence
        else:
            # Truncate to token limit
            words = sentence.split()
            truncated = ""
            for word in words:
                test_text = f"{truncated} {word}".strip()
                if count_tokens(test_text) <= max_tokens - 3:  # Reserve tokens for "..."
                    truncated = test_text
                else:
                    break
            return f"{truncated}..."
    
    # Score all sentences
    scored_sentences = []
    for i, sentence in enumerate(sentences):
        score = score_sentence(sentence, settings.keywords, i, len(sentences))
        scored_sentences.append((sentence, score, i))
        
    # Sort by score (descending)
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    
    # Select best sentences that fit within token limit
    selected_sentences = []
    current_tokens = 0
    
    for sentence, score, original_pos in scored_sentences:
        sentence_tokens = count_tokens(sentence)
        
        # Check if adding this sentence would exceed limits
        if (len(selected_sentences) >= max_sentences or 
            current_tokens + sentence_tokens > max_tokens):
            break
            
        selected_sentences.append((sentence, original_pos))
        current_tokens += sentence_tokens
        
    # If no sentences selected, take the highest scoring one
    if not selected_sentences and scored_sentences:
        best_sentence = scored_sentences[0][0]
        if count_tokens(best_sentence) <= max_tokens:
            return best_sentence
        else:
            # Truncate the best sentence
            words = best_sentence.split()
            truncated = ""
            for word in words:
                test_text = f"{truncated} {word}".strip()
                if count_tokens(test_text) <= max_tokens - 3:
                    truncated = test_text
                else:
                    break
            return f"{truncated}..."
    
    # Sort selected sentences by original position for coherent summary
    selected_sentences.sort(key=lambda x: x[1])
    
    # Combine sentences
    summary = ' '.join([sentence for sentence, _ in selected_sentences])
    
    # Final token check and truncation if needed
    if count_tokens(summary) > max_tokens:
        words = summary.split()
        truncated = ""
        for word in words:
            test_text = f"{truncated} {word}".strip()
            if count_tokens(test_text) <= max_tokens - 3:
                truncated = test_text
            else:
                break
        summary = f"{truncated}..."
    
    return summary if summary else text[:200] + "..."


def create_tldr(text: str, max_tokens: int = 50) -> str:
    """Create a very short TL;DR summary.
    
    Args:
        text: Input text
        max_tokens: Maximum tokens (default 50 for very short summary)
        
    Returns:
        TL;DR summary
    """
    return create_summary(text, max_tokens=max_tokens, max_sentences=1)


def extract_key_phrases(text: str, max_phrases: int = 5) -> List[str]:
    """Extract key phrases from text using simple heuristics.
    
    Args:
        text: Input text
        max_phrases: Maximum number of phrases to extract
        
    Returns:
        List of key phrases
    """
    if not text:
        return []
        
    text_lower = text.lower()
    phrases = []
    
    # Look for quoted phrases
    quoted_phrases = re.findall(r'"([^"]+)"', text)
    for phrase in quoted_phrases[:2]:  # Limit quoted phrases
        if 3 <= len(phrase.split()) <= 6:
            phrases.append(phrase.strip())
            
    # Look for capitalized phrases (potential proper nouns/important terms)
    capitalized = re.findall(r'\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\b', text)
    for phrase in capitalized:
        if 1 <= len(phrase.split()) <= 3 and phrase not in phrases:
            phrases.append(phrase)
            
    # Match against known keywords
    for keyword in settings.keywords:
        if keyword.lower() in text_lower and keyword not in phrases:
            phrases.append(keyword)
            
    return phrases[:max_phrases]
