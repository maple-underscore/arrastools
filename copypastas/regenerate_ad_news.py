#!/usr/bin/env python3
"""
Shuffles all lines in ad_news.txt each time it's run.
"""
import random
from pathlib import Path

def shuffle_ad_news():
    """Shuffle all lines in ad_news.txt and write them back."""
    script_dir = Path(__file__).parent
    ad_news_path = script_dir / "ad_news.txt"
    
    if not ad_news_path.exists():
        print(f"Error: {ad_news_path} does not exist!")
        return
    
    # Read all lines
    with open(ad_news_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Remove trailing newlines but preserve them for writing
    lines = [line.rstrip('\n') for line in lines]
    
    # Shuffle the lines
    random.shuffle(lines)
    
    # Write back with newlines
    with open(ad_news_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"Shuffled {len(lines)} lines in {ad_news_path}")

if __name__ == "__main__":
    shuffle_ad_news()
