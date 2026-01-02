"""Quick test of health pattern matching"""

import re

HEALTH_PATTERNS = [
    r'\b(?:i have|i\'ve got|i got)\s+(?:a\s+)?(?:fever|sick|headache|cold|flu|pain|nausea|cough|dizzy|migraine|stomachache)\b',
    r'\b(?:i feel|i\'m feeling|feeling)\s+(?:sick|ill|unwell|nauseous|dizzy|faint|weak)\b',
    r'\b(?:not feeling well|feeling unwell|under the weather|really sick|very sick|quite sick)\b',
    r'\b(?:my head|my stomach|my back|my throat)\s+(?:hurts|aches|is aching|is sore|is killing me)\b',
    r'\b(?:bad fever|high fever|terrible headache|awful headache|bad headache)\b',
]

# Test text - simulates memory content
test_texts = [
    "User said: I have a really bad fever and headache. Not feeling well at all.\nI responded: ...",
    "I have a really bad fever and headache",
    "i have a fever",
    "I'm feeling sick",
    "not feeling well",
    "bad fever and headache",
]

print("Testing Health Pattern Matching")
print("="*80)

for text in test_texts:
    print(f"\nText: {text[:60]}...")
    text_lower = text.lower()
    
    matched = False
    for i, pattern in enumerate(HEALTH_PATTERNS, 1):
        match = re.search(pattern, text_lower)
        if match:
            print(f"  [MATCH] Pattern {i}: {pattern[:50]}...")
            print(f"  Matched text: '{match.group()}'")
            # Extract context
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 40)
            print(f"  Context: {text[start:end].strip()}")
            matched = True
            break
    
    if not matched:
        print(f"  [NO MATCH]")

print("\n" + "="*80)
