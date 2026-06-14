// =============================================================
// AudioContext 指纹伪装脚本
// 在音频采样中加入微小扰动，破坏指纹的稳定性
// =============================================================

(function() {
    'use strict';

    const NOISE_VALUE = 0.00001;  // 非常微小的噪声

    // 处理 AudioContext
    function patchAudioContext(context) {
        const originalCreateOscillator = context.createOscillator.bind(context);
        const originalCreateAnalyser = context.createAnalyser.bind(context);
        const originalCreateDynamicsCompressor = context.createDynamicsCompressor.bind(context);

        // 拦截createAnalyser，修改getFloatFrequencyData
        context.createAnalyser = function() {
            const analyser = originalCreateAnalyser();
            const originalGetFloatFrequencyData = analyser.getFloatFrequencyData.bind(analyser);
            const originalGetByteFrequencyData = analyser.getByteFrequencyData.bind(analyser);

            analyser.getFloatFrequencyData = function(array) {
                originalGetFloatFrequencyData(array);
                // 添加微小扰动
                for (let i = 0; i < array.length; i++) {
                    array[i] = array[i] + (Math.random() - 0.5) * NOISE_VALUE;
                }
            };

            analyser.getByteFrequencyData = function(array) {
                originalGetByteFrequencyData(array);
                for (let i = 0; i < array.length; i++) {
                    const noise = Math.round((Math.random() - 0.5) * NOISE_VALUE * 255);
                    array[i] = Math.max(0, Math.min(255, array[i] + noise));
                }
            };

            return analyser;
        };

        // 拦截 DynamicsCompressor
        context.createDynamicsCompressor = function() {
            const compressor = originalCreateDynamicsCompressor();
            // 修改关键参数避免指纹一致性
            Object.defineProperty(compressor, 'reduction', {
                get: function() {
                    return -Math.random() * 0.1;
                }
            });
            return compressor;
        };
    }

    // 拦截 AudioContext 创建
    if (window.AudioContext) {
        const OriginalAudioContext = window.AudioContext;
        window.AudioContext = function(...args) {
            const ctx = new OriginalAudioContext(...args);
            patchAudioContext(ctx);
            return ctx;
        };
        window.AudioContext.prototype = OriginalAudioContext.prototype;
    }

    if (window.webkitAudioContext) {
        const OriginalWebkitAudioContext = window.webkitAudioContext;
        window.webkitAudioContext = function(...args) {
            const ctx = new OriginalWebkitAudioContext(...args);
            patchAudioContext(ctx);
            return ctx;
        };
        window.webkitAudioContext.prototype = OriginalWebkitAudioContext.prototype;
    }

    // OfflineAudioContext
    if (window.OfflineAudioContext) {
        const OriginalOfflineAudioContext = window.OfflineAudioContext;
        window.OfflineAudioContext = function(...args) {
            const ctx = new OriginalOfflineAudioContext(...args);
            patchAudioContext(ctx);
            return ctx;
        };
        window.OfflineAudioContext.prototype = OriginalOfflineAudioContext.prototype;
    }

    console.log('[Anti-Detection] AudioContext 指纹伪装已启用');
})();
