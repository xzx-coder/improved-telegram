// =============================================================
// WebGL 指纹伪装脚本
// 修改WebGL的vendor、renderer、unmaskedRenderer等关键属性
// 避免被识别为headless浏览器
// =============================================================

(function() {
    'use strict';

    // 配置参数
    const WEBGL_CONFIG = {
        vendor: 'Google Inc. (NVIDIA)',
        renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)',
        unmaskedVendor: 'Google Inc. (NVIDIA)',
        unmaskedRenderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)',
        maxTextureSize: 16384,
        maxViewportDims: [16384, 16384],
        maxAnisotropy: 16,
        aliasedLineWidthRange: [1, 1],
        aliasedPointSizeRange: [1, 1024]
    };

    // 应用配置到所有WebGL上下文
    function applyWebGLConfig(gl, contextType) {
        const originalGetParameter = gl.getParameter.bind(gl);
        const originalGetExtension = gl.getExtension.bind(gl);
        const originalGetSupportedExtensions = gl.getSupportedExtensions.bind(gl);

        // 重写 getParameter
        gl.getParameter = function(param) {
            // UNMASKED_VENDOR_WEBGL
            if (param === 37445) {
                return WEBGL_CONFIG.unmaskedVendor;
            }
            // UNMASKED_RENDERER_WEBGL
            if (param === 37446) {
                return WEBGL_CONFIG.unmaskedRenderer;
            }
            // VENDOR
            if (param === 7936) {
                return WEBGL_CONFIG.vendor;
            }
            // RENDERER
            if (param === 7937) {
                return WEBGL_CONFIG.renderer;
            }
            // MAX_TEXTURE_SIZE
            if (param === 34076) {
                return WEBGL_CONFIG.maxTextureSize;
            }
            // MAX_VIEWPORT_DIMS
            if (param === 3386) {
                return WEBGL_CONFIG.maxViewportDims;
            }
            // ALIASED_LINE_WIDTH_RANGE
            if (param === 33901) {
                return WEBGL_CONFIG.aliasedLineWidthRange;
            }
            // ALIASED_POINT_SIZE_RANGE
            if (param === 33902) {
                return WEBGL_CONFIG.aliasedPointSizeRange;
            }
            return originalGetParameter(param);
        };

        // 重写 getExtension
        gl.getExtension = function(name) {
            const result = originalGetExtension(name);
            if (result && name === 'WEBGL_debug_renderer_info') {
                // 创建一个伪造的UNMASKED_RENDERER_WEBGL对象
                const proxy = new Proxy(result, {
                    get: function(target, prop) {
                        if (prop === 'UNMASKED_VENDOR_WEBGL') {
                            return 37445;
                        }
                        if (prop === 'UNMASKED_RENDERER_WEBGL') {
                            return 37446;
                        }
                        return target[prop];
                    }
                });
                return proxy;
            }
            return result;
        };

        // 移除 SwiftShader (headless特征)
        gl.getSupportedExtensions = function() {
            const extensions = originalGetSupportedExtensions();
            return extensions.filter(ext => !ext.toLowerCase().includes('swiftshader'));
        };
    }

    // 拦截WebGL上下文创建
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(contextType, contextAttributes) {
        const context = originalGetContext.call(this, contextType, contextAttributes);
        if (context && (contextType === 'webgl' || contextType === 'webgl2' || contextType === 'experimental-webgl')) {
            applyWebGLConfig(context, contextType);
        }
        return context;
    };

    console.log('[Anti-Detection] WebGL 指纹伪装已启用');
})();
