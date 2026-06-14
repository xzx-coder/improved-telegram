// =============================================================
// Canvas 指纹伪装脚本
// 在Canvas绘制结果中加入随机噪声，使得每次/每个浏览器指纹不同
// 但视觉上几乎无差异
// =============================================================

(function() {
    'use strict';

    const NOISE_INTENSITY = 0.5;  // 噪声强度 0-1

    // 保存原始方法
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const originalToBlob = HTMLCanvasElement.prototype.toBlob;
    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;

    // 生成随机扰动种子
    function getNoise() {
        return Math.floor(Math.random() * NOISE_INTENSITY * 10);
    }

    // 修改 toDataURL
    HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
        const context = this.getContext('2d');
        if (context) {
            try {
                const imageData = originalGetImageData.call(context, 0, 0, this.width, this.height);
                const noise = getNoise();
                // 修改部分像素的RGBA值
                for (let i = 0; i < imageData.data.length; i += 4) {
                    // 随机修改RGB通道（非常微小的变化）
                    imageData.data[i] = imageData.data[i] ^ (noise & 1);
                    imageData.data[i + 1] = imageData.data[i + 1] ^ ((noise >> 1) & 1);
                    imageData.data[i + 2] = imageData.data[i + 2] ^ ((noise >> 2) & 1);
                }
                context.putImageData(imageData, 0, 0);
            } catch (e) {
                // 跨域canvas无法修改，忽略
            }
        }
        return originalToDataURL.apply(this, arguments);
    };

    // 修改 toBlob
    HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
        return originalToBlob.call(this, function(blob) {
            callback(blob);
        }, type, quality);
    };

    console.log('[Anti-Detection] Canvas 指纹伪装已启用');
})();
