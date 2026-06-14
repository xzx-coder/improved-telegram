// =============================================================
// 屏幕属性伪装脚本
// 修改 screen.width/height、colorDepth、pixelRatio
// 避免被识别为非标准分辨率
// =============================================================

(function() {
    'use strict';

    const SCREEN_CONFIG = {
        width: 1920,
        height: 1080,
        availWidth: 1920,
        availHeight: 1040,
        colorDepth: 24,
        pixelDepth: 24,
        devicePixelRatio: 1
    };

    // 重写 screen 对象的属性
    Object.defineProperty(screen, 'width', {
        get: () => SCREEN_CONFIG.width,
        configurable: true
    });

    Object.defineProperty(screen, 'height', {
        get: () => SCREEN_CONFIG.height,
        configurable: true
    });

    Object.defineProperty(screen, 'availWidth', {
        get: () => SCREEN_CONFIG.availWidth,
        configurable: true
    });

    Object.defineProperty(screen, 'availHeight', {
        get: () => SCREEN_CONFIG.availHeight,
        configurable: true
    });

    Object.defineProperty(screen, 'colorDepth', {
        get: () => SCREEN_CONFIG.colorDepth,
        configurable: true
    });

    Object.defineProperty(screen, 'pixelDepth', {
        get: () => SCREEN_CONFIG.pixelDepth,
        configurable: true
    });

    // 修改 window.devicePixelRatio
    Object.defineProperty(window, 'devicePixelRatio', {
        get: () => SCREEN_CONFIG.devicePixelRatio,
        configurable: true
    });

    // 修改 window.innerWidth/Height
    Object.defineProperty(window, 'innerWidth', {
        get: () => SCREEN_CONFIG.width,
        configurable: true
    });

    Object.defineProperty(window, 'innerHeight', {
        get: () => SCREEN_CONFIG.height,
        configurable: true
    });

    // 修改 outerWidth/Height
    Object.defineProperty(window, 'outerWidth', {
        get: () => SCREEN_CONFIG.width + 16,
        configurable: true
    });

    Object.defineProperty(window, 'outerHeight', {
        get: () => SCREEN_CONFIG.height + 88,
        configurable: true
    });

    console.log('[Anti-Detection] Screen 属性伪装已启用');
})();
