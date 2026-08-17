/**
 * Whisper-based Voice Input Module
 * Uses @timur00kh/whisper.wasm for offline speech-to-text
 * Fallback to browser SpeechRecognition if Whisper fails
 */

(function() {
    'use strict';

    // State
    let whisperService = null;
    let modelManager = null;
    let whisperSession = null;
    let isWhisperInitialized = false;
    let isWhisperRecording = false;
    let currentCallbacks = null;
    let micStream = null;

    // Browser speech recognition fallback
    let browserRecognition = null;
    let browserRecognitionActive = false;
    // Track if we're using browser SR as primary method
    let useBrowserSR = false;

    const MODEL_SIZE = 'tiny';
    const MODEL_URL = 'https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin';
    const LOCAL_MODEL_URL = '/models/ggml-tiny.bin';

    /**
     * Show small notification toast
     */
    let notificationEl = null;

    function showNotification(message, type = 'info', duration = 4000) {
        hideNotification();

        notificationEl = document.createElement('div');
        notificationEl.id = 'whisper-notification';
        const bgColor = type === 'error' ? '#ff4757' : type === 'success' ? '#2ed573' : '#1a1a2e';
        const borderColor = type === 'error' ? '#ff6b81' : type === 'success' ? '#7bed9f' : 'rgba(255,255,255,0.1)';

        notificationEl.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: ${bgColor};
            color: #ffffff;
            padding: 12px 18px;
            border-radius: 10px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 13px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            z-index: 99999;
            display: flex;
            align-items: center;
            gap: 10px;
            max-width: 300px;
            border: 1px solid ${borderColor};
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s ease;
        `;

        const iconSvg = type === 'error'
            ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
            : type === 'success'
            ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
            : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';

        notificationEl.innerHTML = iconSvg + '<span>' + message + '</span>';
        document.body.appendChild(notificationEl);

        requestAnimationFrame(() => {
            notificationEl.style.opacity = '1';
            notificationEl.style.transform = 'translateY(0)';
        });

        if (duration > 0) {
            setTimeout(hideNotification, duration);
        }
    }

    function hideNotification() {
        if (notificationEl) {
            notificationEl.style.opacity = '0';
            notificationEl.style.transform = 'translateY(20px)';
            setTimeout(() => {
                if (notificationEl && notificationEl.parentNode) {
                    document.body.removeChild(notificationEl);
                }
                notificationEl = null;
            }, 300);
        }
    }

    function showDownloadProgress() {
        hideNotification();

        notificationEl = document.createElement('div');
        notificationEl.id = 'whisper-notification';
        notificationEl.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #ffffff;
            padding: 14px 18px;
            border-radius: 10px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 13px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
            z-index: 99999;
            max-width: 280px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s ease;
        `;

        notificationEl.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00d4ff" stroke-width="2">
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                    <line x1="12" x2="12" y1="19" y2="22"/>
                </svg>
                <span style="font-weight: 500;">下载语音模型中...</span>
            </div>
            <div style="width: 100%; height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px; overflow: hidden;">
                <div id="whisper-progress-bar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #00d4ff, #00ff88); border-radius: 2px; transition: width 0.2s;"></div>
            </div>
            <div id="whisper-progress-text" style="margin-top: 6px; color: #8892b0; font-size: 12px;">准备中...</div>
        `;
        document.body.appendChild(notificationEl);

        requestAnimationFrame(() => {
            notificationEl.style.opacity = '1';
            notificationEl.style.transform = 'translateY(0)';
        });
    }

    function updateProgress(percent, status) {
        const bar = document.getElementById('whisper-progress-bar');
        const text = document.getElementById('whisper-progress-text');
        if (bar) bar.style.width = percent + '%';
        if (text) text.textContent = status || (percent + '%');
    }

    /**
     * Initialize browser SpeechRecognition as fallback
     */
    function initBrowserRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            return null;
        }

        browserRecognition = new SpeechRecognition();
        browserRecognition.continuous = true;
        browserRecognition.interimResults = true;
        browserRecognition.lang = 'zh-CN';

        browserRecognition.onstart = () => {
            browserRecognitionActive = true;
            useBrowserSR = true;
            currentCallbacks?.onStart?.();
            showNotification('正在聆听...请说话', 'info', 3000);
        };

        browserRecognition.onresult = (event) => {
            const transcripts = Array.from(event.results)
                .map(result => result[0].transcript)
                .join('');
            if (transcripts) {
                currentCallbacks?.onTranscription?.(transcripts);
            }
        };

        browserRecognition.onerror = (event) => {
            console.error('[Voice] Browser SR error:', event.error);
            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                showNotification('麦克风权限被拒绝，请在浏览器设置中允许', 'error');
                currentCallbacks?.onError?.(new Error('microphone-permission-denied'));
            } else if (event.error === 'no-speech') {
                // Just log and continue listening - no-speech is not a fatal error
                console.log('[Voice] No speech detected, continuing...');
                showNotification('未检测到语音，请对准麦克风说话', 'info', 2000);
            } else if (event.error === 'aborted') {
                console.log('[Voice] Recognition aborted');
            } else {
                currentCallbacks?.onError?.(new Error(event.error));
            }
        };

        browserRecognition.onend = () => {
            browserRecognitionActive = false;
            // Only call onEnd if we're not recording with Whisper
            if (!isWhisperRecording) {
                currentCallbacks?.onEnd?.();
            }
        };

        return browserRecognition;
    }

    /**
     * Initialize Whisper service - tries multiple sources
     */
    async function initWhisper(onReady, onError) {
        if (isWhisperInitialized) {
            onReady?.();
            return;
        }

        // Check if already tried and failed - use browser SR directly
        if (window.localStorage && window.localStorage.getItem('whisper_failed') === 'true') {
            console.log('[Whisper] Previously failed, using browser SR');
            const sr = initBrowserRecognition();
            if (sr) {
                isWhisperInitialized = true;
                useBrowserSR = true;
                onReady?.();
                return;
            }
        }

        try {
            console.log('[Whisper] Initializing...');
            showDownloadProgress();

            // Dynamic import
            const { WhisperWasmService, ModelManager, convertFromMediaStream } = await import('@timur00kh/whisper.wasm');

            whisperService = new WhisperWasmService({ logLevel: 1 });
            modelManager = new ModelManager({ logLevel: 1 });

            // Check WASM support
            const isSupported = await whisperService.checkWasmSupport();
            if (!isSupported) {
                throw new Error('WebAssembly is not supported');
            }

            let modelData = null;
            let loadError = null;

            // Try local model first (if user manually downloaded)
            try {
                updateProgress(5, '检查本地模型...');
                const localResponse = await fetch(LOCAL_MODEL_URL, { method: 'HEAD' });
                if (localResponse.ok) {
                    console.log('[Whisper] Loading from local...');
                    updateProgress(10, '从本地加载...');
                    const response = await fetch(LOCAL_MODEL_URL);
                    if (response.ok) {
                        modelData = await response.arrayBuffer();
                    }
                }
            } catch (e) {
                console.log('[Whisper] Local model not found, trying remote...');
            }

            // Try hf-mirror if no local model
            if (!modelData) {
                try {
                    console.log('[Whisper] Loading model from hf-mirror...');
                    updateProgress(10, '从镜像下载...');
                    modelData = await modelManager.loadModelByUrl(
                        MODEL_URL,
                        (progress) => {
                            updateProgress(Math.round(progress), '下载中 ' + Math.round(progress) + '%');
                        }
                    );
                } catch (e) {
                    loadError = e;
                    console.log('[Whisper] hf-mirror failed:', e.message);
                }
            }

            // Both sources failed
            if (!modelData) {
                throw loadError || new Error('无法下载模型');
            }

            whisperSession = whisperService.createSession();
            isWhisperInitialized = true;
            useBrowserSR = false;
            if (window.localStorage) {
                window.localStorage.removeItem('whisper_failed');
            }

            updateProgress(100, '加载完成!');
            setTimeout(() => {
                hideNotification();
                showNotification('语音模型已就绪', 'success');
                onReady?.();
            }, 500);

        } catch (err) {
            console.error('[Whisper] Init failed:', err);
            hideNotification();

            // Mark as failed for future sessions
            if (window.localStorage) {
                window.localStorage.setItem('whisper_failed', 'true');
            }

            // Fall back to browser SpeechRecognition
            const sr = initBrowserRecognition();
            if (sr) {
                isWhisperInitialized = true;
                useBrowserSR = true;
                showNotification('Whisper下载失败，将使用浏览器语音识别', 'info', 5000);
                onReady?.();
            } else {
                showNotification('语音识别不可用: ' + err.message, 'error');
                onError?.(err);
            }
        }
    }

    /**
     * Start voice recording and transcription
     */
    async function startRecording(callbacks) {
        currentCallbacks = callbacks;

        if (!isWhisperInitialized) {
            await initWhisper(
                () => startRecording(callbacks),
                (err) => callbacks.onError?.(err)
            );
            return;
        }

        if (isWhisperRecording) {
            console.warn('[Voice] Already recording');
            return;
        }

        // Use browser SpeechRecognition
        if (useBrowserSR && browserRecognition) {
            try {
                browserRecognition.start();
            } catch (e) {
                console.error('[Voice] Browser SR start error:', e);
                currentCallbacks?.onError?.(e);
            }
            return;
        }

        // Use Whisper for transcription
        try {
            console.log('[Whisper] Requesting microphone...');
            micStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    sampleRate: 16000
                }
            });

            isWhisperRecording = true;
            currentCallbacks.onStart?.();

            const { convertFromMediaStream } = await import('@timur00kh/whisper.wasm');

            const { audioData } = await convertFromMediaStream(micStream, {
                normalize: true,
                recordingDurationMs: 15000
            });

            console.log('[Whisper] Processing audio, length:', audioData.length);

            await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Transcribe timeout'));
                }, 60000);

                whisperSession.transcribe(audioData, (segment) => {
                    console.log('[Whisper] Segment:', segment);
                    if (segment && segment.text) {
                        currentCallbacks.onTranscription?.(segment.text);
                    }
                }, {
                    language: 'zh',
                    threads: 4,
                    translate: false
                }).then((result) => {
                    clearTimeout(timeout);
                    console.log('[Whisper] Transcription complete:', result);
                    resolve(result);
                }).catch((err) => {
                    clearTimeout(timeout);
                    reject(err);
                });
            });

        } catch (err) {
            console.error('[Whisper] Recording error:', err);
            currentCallbacks.onError?.(err);
        } finally {
            isWhisperRecording = false;
            if (micStream) {
                micStream.getTracks().forEach(t => t.stop());
                micStream = null;
            }
            currentCallbacks.onEnd?.();
        }
    }

    /**
     * Stop recording
     */
    function stopRecording() {
        isWhisperRecording = false;
        if (micStream) {
            micStream.getTracks().forEach(t => t.stop());
            micStream = null;
        }
        if (browserRecognition && browserRecognitionActive) {
            try {
                browserRecognition.stop();
            } catch (e) {
                console.log('[Voice] Browser SR stop error:', e);
            }
        }
    }

    // Export
    window.WhisperVoice = {
        init: initWhisper,
        start: startRecording,
        stop: stopRecording,
        isReady: () => isWhisperInitialized,
        isRecording: () => isWhisperRecording || browserRecognitionActive
    };

})();