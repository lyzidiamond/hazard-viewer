# Changelog

## 10/20/26

### Core app logic changes

**SIGNIFICANT UPDATE ALERT!!!**

This update changes the core logic of the hazard risk assessment. Instead of Claude generating the risk level, I added the logic directly in code. This wasn't significant for the original use case of this app (show what's possible with Render) but my current goal is to make the app more of a federal data aggregator/visualizer for natural hazards.

The new logic is very simple: get all the federal disaster declarations and add them together with the ones since 2011 weighed by 1.5. A score of 50 or above is very high, 30-50 is high, 15-30 moderate, 5-15 low, 0-5 very low. Federal disaster declarations are _not_ the only way to determine risk. Next step is to add in the actual risk index and maybe some other sources as well. I must disclaim: do not rely on this app for your personal safety! It's just a tool! Do your own research!

All Claude is doing now is generating the narrative. It uses the federal data and the flood hazard data, but it also does its own LLM magic to give its opinion.

Options for the future:
- make this app a straight up assessment/viewer for federal natural hazard data across the board. Click a place and see your flood zone, see disaster declarations, whatever other info I can get. AGOL GIS in the broswer style. No analysis, or a non-AI analysis. Can include any government documents that reference that area if they're easily searchable/available, like the RiskMAP product (I don't know what else is out there right now).

### On the frontend

The disaster declarations themselves are now loaded directly in the code rather than generated via the call to Claude. 

## 5/27/26

- **Rate limiting:** Added slowapi for per-IP rate limiting on the narrative endpoint. The app now returns a 429 with a Retry-After header when the limit is hit and displays a message to the user.
- **NFHL timeout handling:** Raised timeouts from the National Flood Hazard Layer from 10 seconds to 30 seconds. Timeouts return an "unavailable" state.
- **/narrative/stream endpoint:** Added a streaming endpoint to enable streaming text from Claude instead of waiting for the whole narrative to generate first.
- **CSS updates:** Removed Pico CSS and added custom styling and fonts. Added a mobile layout. Map uses `fitBounds` instead of `flyTo` to ensure entire selected region is in the map frame.