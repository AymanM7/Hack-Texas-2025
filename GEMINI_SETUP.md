# Gemini API Setup Guide

## ⚠️ SECURITY WARNING

**Do NOT commit your API key to the repository.** The API key you provided in plaintext should be treated as compromised and regenerated immediately.

## Steps to Configure Gemini API Securely

### 1. Add Gemini API Key to `.env` file

Create or update your `.env` file in the project root:

```bash
BASE_API_URL=https://api.openf1.org/v1/
GEMINI_API_KEY=your_api_key_here
```

**Replace `your_api_key_here` with your actual Gemini API key.**

### 2. Regenerate Your API Key (Important!)

Since the API key was shared in plaintext:

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click on your API key
3. Click "Regenerate" to create a new key
4. Replace the old key in your `.env` file with the new one
5. Update this `.env` file with the new key

### 3. Install Updated Dependencies

```bash
pip install -r requirements.txt
```

This will install `google-generativeai` needed for Gemini integration.

### 4. Verify Setup

Run the app:

```bash
streamlit run main.py
```

Navigate to the "🤖 Simulation Visualizer" section and select a driver. The Gemini analysis should work once the API key is properly configured.

## Features

The Simulation Visualizer includes:

- **Driver Selection Dropdown**: Choose any driver in the session
- **Overall Race Feedback**: AI-generated summary of the driver's performance
- **Lap-by-Lap Analysis**: Individual analysis for each lap including:
  - What happened in that lap
  - Performance insights
  - Pit stop indicators
  - Clickable timestamps in format `session_key:lap_number`

## Limitations

- Analysis is cached (`@st.cache_data`) to minimize API calls and costs
- Free tier of Gemini API has rate limits—monitor your usage
- First run for a driver will take longer (analysis is generated)
- Subsequent runs for the same driver/session will use cached results

## Troubleshooting

**"Error analyzing laps" message:**
- Check that `GEMINI_API_KEY` is set in `.env`
- Verify the API key is valid and has not exceeded rate limits
- Check your internet connection

**No analysis showing up:**
- Ensure lap data is available (visible in the lap time chart above)
- Make sure at least one driver has lap data
- Wait for the spinner to complete

## Cost Considerations

Each lap analysis makes 2 API calls to Gemini (one for per-lap, one for overall):
- **Per-lap analysis**: ~0.5 calls per lap
- **Overall feedback**: 1 call per driver

Consider the number of laps when analyzing multiple drivers to manage API costs.
