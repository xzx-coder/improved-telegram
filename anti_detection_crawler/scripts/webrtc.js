// =============================================================
// WebRTC 隐藏脚本
// 阻止WebRTC泄露真实本地IP地址
// =============================================================

(function() {
    'use strict';

    // 拦截 RTCPeerConnection
    if (window.RTCPeerConnection) {
        const OriginalRTCPeerConnection = window.RTCPeerConnection;
        const OriginalwebkitRTCPeerConnection = window.webkitRTCPeerConnection;

        function PatchedRTCPeerConnection(config, constraints) {
            const pc = new OriginalRTCPeerConnection(config, constraints);

            // 拦截 createOffer
            const originalCreateOffer = pc.createOffer.bind(pc);
            pc.createOffer = async function(options) {
                const offer = await originalCreateOffer(options);
                // 修改SDP，移除候选地址中的本地IP
                if (offer && offer.sdp) {
                    offer.sdp = filterLocalIPs(offer.sdp);
                }
                return offer;
            };

            // 拦截 createAnswer
            const originalCreateAnswer = pc.createAnswer.bind(pc);
            pc.createAnswer = async function(options) {
                const answer = await originalCreateAnswer(options);
                if (answer && answer.sdp) {
                    answer.sdp = filterLocalIPs(answer.sdp);
                }
                return answer;
            };

            // 拦截 onicecandidate
            Object.defineProperty(pc, 'onicecandidate', {
                get: function() { return this._onicecandidate; },
                set: function(fn) {
                    this._onicecandidate = function(event) {
                        if (event && event.candidate && event.candidate.candidate) {
                            event.candidate.candidate = filterCandidate(event.candidate.candidate);
                        }
                        fn.call(this, event);
                    }.bind(pc);
                }
            });

            return pc;
        }

        // 过滤SDP中的本地IP
        function filterLocalIPs(sdp) {
            if (!sdp) return sdp;
            return sdp.replace(/(c=IN IP4)(\d+\.\d+\.\d+\.\d+)/g, (match, prefix) => {
                return prefix + '0.0.0.0';
            });
        }

        // 过滤候选地址
        function filterCandidate(candidate) {
            return candidate.replace(/(\d+\.\d+\.\d+\.\d+)/g, (match) => {
                // 保留公网IP
                if (isPrivateIP(match)) {
                    return '0.0.0.0';
                }
                return match;
            });
        }

        function isPrivateIP(ip) {
            const parts = ip.split('.');
            if (parts.length !== 4) return false;
            const a = parseInt(parts[0], 10);
            const b = parseInt(parts[1], 10);
            if (a === 10) return true;
            if (a === 172 && b >= 16 && b <= 31) return true;
            if (a === 192 && b === 168) return true;
            if (a === 127) return true;
            return false;
        }

        PatchedRTCPeerConnection.prototype = OriginalRTCPeerConnection.prototype;

        window.RTCPeerConnection = PatchedRTCPeerConnection;
        if (OriginalwebkitRTCPeerConnection) {
            window.webkitRTCPeerConnection = PatchedRTCPeerConnection;
        }
    }

    console.log('[Anti-Detection] WebRTC 隐藏已启用');
})();
