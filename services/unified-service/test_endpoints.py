#!/usr/bin/env python3
"""
Test script for the unified VoiceMart service.
Run this after starting the service to test all endpoints.
"""

import requests
import json
import os

# Service URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health check: {response.status_code} - {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_query_processing():
    """Test query processing endpoint"""
    print("\n🔍 Testing query processing...")
    
    test_queries = [
        "find Nike shoes under $100",
        "add 2 packs of Milo to cart",
        "show me the cart",
        "checkout"
    ]
    
    for query in test_queries:
        try:
            payload = {
                "text": query,
                "user_id": "test_user",
                "locale": "en-US"
            }
            response = requests.post(f"{BASE_URL}/v1/query:process", json=payload)
            result = response.json()
            print(f"✅ Query: '{query}'")
            print(f"   Intent: {result.get('intent')}")
            print(f"   Reply: {result.get('reply')}")
            print(f"   Confidence: {result.get('confidence')}")
            print()
        except Exception as e:
            print(f"❌ Query processing failed for '{query}': {e}")

def test_stt_with_sample_audio():
    """Test STT with sample audio file"""
    print("🔍 Testing Speech-to-Text...")
    
    # Check if sample audio exists
    sample_audio_path = "/Users/enithsamarasinghe/Desktop/GitHub/VoiceMart-Shopping-Assistant/services/voice-agent/sample_audio/voice1.mp3"
    
    if not os.path.exists(sample_audio_path):
        print("❌ Sample audio file not found. Please provide an audio file for testing.")
        return False
    
    try:
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('voice1.mp3', audio_file, 'audio/mpeg')}
            response = requests.post(f"{BASE_URL}/v1/stt:transcribe", files=files)
            result = response.json()
            print(f"✅ STT Result:")
            print(f"   Text: {result.get('text', 'No text detected')}")
            print(f"   Language: {result.get('language', 'Unknown')}")
            print(f"   Confidence: {result.get('confidence', 'N/A')}")
            return True
    except Exception as e:
        print(f"❌ STT test failed: {e}")
        return False

def test_voice_understanding():
    """Test complete voice understanding pipeline"""
    print("\n🔍 Testing Voice Understanding...")
    
    sample_audio_path = "/Users/enithsamarasinghe/Desktop/GitHub/VoiceMart-Shopping-Assistant/services/voice-agent/sample_audio/voice1.mp3"
    
    if not os.path.exists(sample_audio_path):
        print("❌ Sample audio file not found. Skipping voice understanding test.")
        return False
    
    try:
        with open(sample_audio_path, 'rb') as audio_file:
            files = {'file': ('voice1.mp3', audio_file, 'audio/mpeg')}
            data = {
                'user_id': 'test_user',
                'locale': 'en-US'
            }
            response = requests.post(f"{BASE_URL}/v1/voice:understand", files=files, data=data)
            result = response.json()
            print(f"✅ Voice Understanding Result:")
            print(f"   Transcript: {result.get('transcript', {}).get('text', 'No text')}")
            print(f"   Intent: {result.get('query', {}).get('intent', 'Unknown')}")
            print(f"   Reply: {result.get('query', {}).get('reply', 'No reply')}")
            return True
    except Exception as e:
        print(f"❌ Voice understanding test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting VoiceMart Unified Service Tests")
    print("=" * 50)
    
    # Test health first
    if not test_health():
        print("❌ Service is not running. Please start the service first.")
        return
    
    # Test query processing
    test_query_processing()
    
    # Test STT
    test_stt_with_sample_audio()
    
    # Test voice understanding
    test_voice_understanding()
    
    print("\n" + "=" * 50)
    print("🎉 Testing completed!")
    print("\n📖 For interactive testing, visit: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
