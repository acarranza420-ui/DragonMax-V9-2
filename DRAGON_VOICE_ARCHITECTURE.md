# Dragon Voice + Dragon AI

Dragon Voice is a modular control layer for DragonMax V12. It is designed so Kodi remains fully usable if voice services are unavailable.

## Core goals

- Natural-language control for common DragonMax and Kodi actions.
- Fast local intent handling for routine commands.
- Optional AI fallback for questions and future richer commands.
- Remote-control parity: every important voice action must remain available manually.
- Confirmation before destructive actions.
- Fire TV Stick 4K Max stability first.

## Current Kodi-side implementation

The `service.dragonmax.voice` addon starts with Kodi and exposes a small authenticated LAN bridge on port `8765`.

Supported local intents currently include:

- Open home, Movies, TV Shows, and Dragon Portal.
- Switch among all six DragonMax realms.
- Select Maximum Speed, Balanced, or Visual Quality performance mode.
- Basic system-health response.
- Open the maintenance path for safe cache cleanup.
- Receive search requests.
- Detect destructive requests and require confirmation rather than executing them directly.

The service stores a randomly generated bridge token in its Kodi addon profile. LAN commands must provide that token in the `X-Dragon-Token` header.

## Voice input path

Fire OS owns the Alexa remote microphone and Kodi should not depend on direct raw-microphone access. DragonMax therefore treats speech capture as a separate input layer.

Recommended input paths, in order:

1. A DragonMax companion app or shortcut on phone/tablet that performs speech-to-text and posts the resulting text to the Kodi bridge.
2. A supported microphone/input device exposed to a companion process.
3. Manual text input as a debugging and accessibility fallback.

The bridge accepts text, not raw audio. This keeps Kodi lightweight and lets speech recognition improve independently without destabilizing the build.

## Bridge protocol

`POST /command`

Headers:

- `Content-Type: application/json`
- `X-Dragon-Token: <paired token>`

Body example:

```json
{
  "text": "Dragon, switch to Arcane Dominion and open my continue watching",
  "confirmed": false
}
```

The response includes whether the command succeeded, the resolved intent, a short message, and whether confirmation is required.

## Safety model

Destructive intents such as factory reset, full data clearing, or backup restoration are never executed directly by the voice service. They are recognized and routed into a confirmation-safe flow.

## AI layer

Routine commands should stay local because local execution is faster and more reliable. An optional external AI endpoint can later handle troubleshooting, natural-language questions, and multi-step planning. Any AI-produced device action must still pass through the same local allow-list and safety checks.

## Release rule

Dragon Voice is modular. A voice or AI outage must not block Kodi startup, home navigation, playback, Dragon Portal, or remote control operation.
