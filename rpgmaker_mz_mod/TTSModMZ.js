//=============================================================================
// RPG Maker MZ - Universal Kokoro TTS Mod (NW.js / Node.js TCP)
//=============================================================================
/*:
 * @target MZ
 * @plugindesc Universal Kokoro TTS Mod for RPG Maker MZ games running on NW.js.
 * @author DeepMind Pair Programming / Antigravity
 * 
 * @help
 * Universal Kokoro TTS Mod for RPG Maker MZ:
 * - Reads dialogue lines with gender-correct character voices via Kokoro TTS.
 * - Auto-forward support: advances text after audio completes.
 * - Keyboard shortcuts:
 *     V : Toggle TTS Audio On/Off
 *     A : Toggle Auto-Forward Mode On/Off
 *     + : Increase Speech Speed (+0.1)
 *     - : Decrease Speech Speed (-0.1)
 */

(function () {
    "use strict";

    if (window._TTSModMZ_Loaded) return;
    window._TTSModMZ_Loaded = true;

    // Verify Node.js / NW.js environment
    const isNwjs = typeof require === "function" && typeof process === "object";
    if (!isNwjs) {
        console.warn("[TTSModMZ] Node.js net module not available outside NW.js.");
        return;
    }

    const net = require("net");
    const fs = require("fs");
    const path = require("path");

    const TTSMod = {
        host: "127.0.0.1",
        port: 5050,
        socket: null,
        connected: false,
        reconnectTimer: null,
        enabled: true,
        autoForward: false,
        playbackFinished: false,
        speed: 1.0,
        currentVoice: "am_onyx",
        defaultVoice: "am_onyx",
        voiceMap: {},
        lastSpokenKey: "",

        init() {
            this.loadVoiceMap();
            this.connect();
            this.setupKeyboardListeners();
            console.log("[TTSModMZ] Initialized successfully.");
        },

        loadVoiceMap() {
            try {
                const searchPaths = [
                    path.join(process.cwd(), "voice_map.json"),
                    path.join(process.cwd(), "data", "voice_map.json"),
                    path.join(__dirname, "..", "..", "voice_map.json"),
                    path.join(__dirname, "voice_map.json")
                ];

                for (const p of searchPaths) {
                    if (fs.existsSync(p)) {
                        const raw = fs.readFileSync(p, "utf8");
                        this.voiceMap = JSON.parse(raw);
                        console.log(`[TTSModMZ] Loaded voice_map from: ${p} (${Object.keys(this.voiceMap).length} entries)`);
                        return;
                    }
                }
                console.warn("[TTSModMZ] voice_map.json not found in search paths. Using defaults.");
            } catch (err) {
                console.error("[TTSModMZ] Failed to load voice_map.json:", err);
            }
        },

        connect() {
            if (this.socket) {
                try { this.socket.destroy(); } catch (_) {}
            }

            const socket = new net.Socket();
            this.socket = socket;

            socket.connect(this.port, this.host, () => {
                this.connected = true;
                console.log(`[TTSModMZ] Connected to TTS server at ${this.host}:${this.port}`);
                if (this.reconnectTimer) {
                    clearInterval(this.reconnectTimer);
                    this.reconnectTimer = null;
                }
            });

            socket.on("data", (data) => {
                const text = data.toString("utf8");
                const lines = text.split("\n");
                for (const line of lines) {
                    const trimmed = line.trim();
                    if (trimmed === "PLAYBACK_DONE") {
                        this.playbackFinished = true;
                    }
                }
            });

            socket.on("error", (err) => {
                this.connected = false;
            });

            socket.on("close", () => {
                this.connected = false;
                if (!this.reconnectTimer) {
                    this.reconnectTimer = setInterval(() => {
                        this.connect();
                    }, 3000);
                    if (this.reconnectTimer && typeof this.reconnectTimer.unref === "function") {
                        this.reconnectTimer.unref();
                    }
                }
            });
        },

        cleanText(text) {
            if (!text) return "";
            let cleaned = String(text);

            // 0. Normalize ASCII 27 escape byte and multiple backslashes to a single backslash
            cleaned = cleaned.replace(/[\x1b\\]+/g, "\\");

            // 1. Convert variable and actor escape codes if available in game
            try {
                if (window.$gameVariables && window.$gameActors) {
                    cleaned = cleaned.replace(/\\V\[(\d+)\]/gi, (_, p1) => $gameVariables.value(parseInt(p1)));
                    cleaned = cleaned.replace(/\\N\[(\d+)\]/gi, (_, p1) => {
                        const a = $gameActors.actor(parseInt(p1));
                        return a ? a.name() : (parseInt(p1) === 11 ? "Liora" : "Reid");
                    });
                    cleaned = cleaned.replace(/\\P\[(\d+)\]/gi, (_, p1) => {
                        const m = $gameParty ? $gameParty.members()[parseInt(p1) - 1] : null;
                        return m ? m.name() : "Reid";
                    });
                }
            } catch (_) {}

            // 2. Handle specific RPG Maker / dev typos and fallbacks for actor names
            cleaned = cleaned.replace(/\\\[N\]1/gi, "Reid");
            cleaned = cleaned.replace(/\\N\[\]/gi, "Reid");
            cleaned = cleaned.replace(/\\n\[1\]/gi, "Reid");
            cleaned = cleaned.replace(/\\N\[11\]/gi, "Liora");
            cleaned = cleaned.replace(/\\N\[\d*\]/gi, "Reid");
            cleaned = cleaned.replace(/\\V\[\d+\]/gi, "");

            // 3. Strip RPG Maker control and formatting codes (\C[n], \I[n], \FS[n], \PX[n], etc.)
            cleaned = cleaned.replace(/\\c\[\d+\]/gi, "");
            cleaned = cleaned.replace(/\\I,/gi, " ");
            cleaned = cleaned.replace(/\\[A-Za-z]+\[[^\]]*\]/g, " ");
            cleaned = cleaned.replace(/\\[\.\|\^!><{}\\$#]/g, " ");
            cleaned = cleaned.replace(/\\/g, " ");

            // 4. Normalize quotes, apostrophes and dashes
            cleaned = cleaned.replace(/[’‘´`′ʼ]/g, "'");
            cleaned = cleaned.replace(/[“”„]/g, '"');
            cleaned = cleaned.replace(/‑/g, "-");
            cleaned = cleaned.replace(/[—–]/g, " — ");
            cleaned = cleaned.replace(/…/g, "...");

            // 5. Remove hearts, music symbols, emojis and invisible variation selectors
            cleaned = cleaned.replace(/[♡♥❤🖤★☆♪♫♬🎵☕]/g, "");
            cleaned = cleaned.replace(/[\uFE0E\uFE0F\u200B-\u200D\uFEFF]/g, "");

            // 6. Ensure line breaks between sentences create natural speech pause
            cleaned = cleaned.replace(/([^\s.?!,:;—~])\s*\r?\n\s*/g, "$1. ");

            // 7. Collapse whitespace
            cleaned = cleaned.replace(/\s+/g, " ").trim();
            return cleaned;
        },

        resolveVoice(rawSpeaker) {
            let speaker = String(rawSpeaker || "").trim();

            // Strip formatting from speaker name (e.g. \c[18]Morrigan -> Morrigan)
            speaker = speaker.replace(/[\x1b\\]+/g, "\\");
            speaker = speaker.replace(/\\c\[\d+\]/gi, "");
            speaker = speaker.replace(/\\[A-Za-z]+\[[^\]]*\]/g, "").trim();
            speaker = speaker.replace(/\\[\.\|\^!><{}\\$#]/g, "").trim();
            speaker = speaker.replace(/\\/g, "").trim();

            if (!speaker) {
                return this.voiceMap["default"] || this.defaultVoice;
            }

            // Direct match in voiceMap
            if (this.voiceMap[speaker]) {
                return this.voiceMap[speaker];
            }

            // Case-insensitive match
            const lowerSpeaker = speaker.toLowerCase();
            for (const key of Object.keys(this.voiceMap)) {
                if (key.toLowerCase() === lowerSpeaker) {
                    return this.voiceMap[key];
                }
            }

            // Protagonist checks
            if (["reid", "mc", "player", "you", "hero"].includes(lowerSpeaker)) {
                return this.voiceMap["Reid"] || "am_onyx";
            }

            // Heuristic gender fallbacks
            const femaleHints = ["girl", "woman", "maid", "queen", "princess", "lady", "nun", "witch", "sister", "fairy", "mother"];
            const maleHints = ["man", "boy", "king", "prince", "lord", "dad", "father", "guard", "knight", "orc", "goblin", "bandit", "thug"];

            if (femaleHints.some(h => lowerSpeaker.includes(h))) {
                return "af_heart";
            }
            if (maleHints.some(h => lowerSpeaker.includes(h))) {
                return "am_eric";
            }

            return this.defaultVoice;
        },

        speak(rawText, rawSpeaker) {
            if (!this.enabled || !this.connected) return;

            const text = this.cleanText(rawText);
            if (!text) return;

            const speaker = rawSpeaker || "";
            const key = `${speaker}:::${text}`;
            if (this.lastSpokenKey === key) return;
            this.lastSpokenKey = key;

            const voice = this.resolveVoice(speaker);
            this.currentVoice = voice;
            this.playbackFinished = false;

            try {
                // Protocol invariant: STOP -> SET_VOICE -> SET_SPEED -> DIALOGUE TEXT
                this.socket.write("STOP\n");
                this.socket.write(`SET_VOICE:${voice}\n`);
                this.socket.write(`SET_SPEED:${this.speed.toFixed(2)}\n`);
                this.socket.write(`${text}\n`);
            } catch (err) {
                console.error("[TTSModMZ] Socket write error:", err);
            }
        },

        stop() {
            if (!this.connected) return;
            try {
                this.socket.write("STOP\n");
            } catch (_) {}
        },

        setupKeyboardListeners() {
            if (typeof window.addEventListener !== "function") return;
            window.addEventListener("keydown", (e) => {
                // Ignore if typing in text inputs
                const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : "";
                if (tag === "input" || tag === "textarea") return;

                // V (86) : Toggle TTS On/Off
                if (e.keyCode === 86) {
                    this.enabled = !this.enabled;
                    if (!this.enabled) this.stop();
                    SoundManager.playCursor();
                    console.log(`[TTSModMZ] TTS Vozes: ${this.enabled ? "LIGADO" : "DESLIGADO"}`);
                }

                // A (65) : Toggle Auto-Forward
                if (e.keyCode === 65) {
                    this.autoForward = !this.autoForward;
                    SoundManager.playDecision();
                    console.log(`[TTSModMZ] Modo Automatico (Auto-Forward): ${this.autoForward ? "LIGADO" : "DESLIGADO"}`);
                }

                // + (107 or 187 with shift) : Speed up
                if (e.keyCode === 107 || (e.keyCode === 187 && e.shiftKey)) {
                    this.speed = Math.min(2.5, this.speed + 0.1);
                    console.log(`[TTSModMZ] Velocidade TTS: ${this.speed.toFixed(2)}x`);
                }

                // - (109 or 189) : Speed down
                if (e.keyCode === 109 || e.keyCode === 189) {
                    this.speed = Math.max(0.5, this.speed - 0.1);
                    console.log(`[TTSModMZ] Velocidade TTS: ${this.speed.toFixed(2)}x`);
                }
            });
        }
    };

    TTSMod.init();
    window.TTSMod = TTSMod;

    //=============================================================================
    // RPG Maker MZ Window Hooks (Additive Modding)
    //=============================================================================

    // 1. Hook Window_Message.prototype.startMessage
    const _Window_Message_startMessage = Window_Message.prototype.startMessage;
    Window_Message.prototype.startMessage = function () {
        _Window_Message_startMessage.call(this);

        try {
            const rawText = $gameMessage.allText();
            let rawSpeaker = $gameMessage.speakerName();

            if (!rawSpeaker && this._nameBoxWindow && typeof this._nameBoxWindow._name === "string") {
                rawSpeaker = this._nameBoxWindow._name;
            }

            TTSMod.speak(rawText, rawSpeaker);
        } catch (err) {
            console.error("[TTSModMZ] Error in Window_Message.startMessage hook:", err);
        }
    };

    // 2. Hook Window_Message.prototype.updateInput for Auto-Forward and manual stop
    const _Window_Message_updateInput = Window_Message.prototype.updateInput;
    Window_Message.prototype.updateInput = function () {
        // If auto-forward is enabled, pause is waiting, playback finished, and no sub-window active:
        if (TTSMod.autoForward && TTSMod.playbackFinished && this.pause && !this.isAnySubWindowActive()) {
            TTSMod.playbackFinished = false;
            Input.update();
            this.pause = false;
            if (!this._textState) {
                this.terminateMessage();
            }
            return true;
        }

        // When user manually advances dialogue, stop audio immediately
        if (this.pause && this.isTriggered()) {
            TTSMod.stop();
        }

        return _Window_Message_updateInput.call(this);
    };

    // 3. Hook Window_ScrollText.prototype.startMessage for narrative scrolling text
    const _Window_ScrollText_startMessage = Window_ScrollText.prototype.startMessage;
    Window_ScrollText.prototype.startMessage = function () {
        _Window_ScrollText_startMessage.call(this);

        try {
            const rawText = $gameMessage.allText();
            TTSMod.speak(rawText, "narrator");
        } catch (err) {
            console.error("[TTSModMZ] Error in Window_ScrollText.startMessage hook:", err);
        }
    };

})();
