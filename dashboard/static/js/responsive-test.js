// File: dashboard/static/js/responsive-test.js

/**
 * Utility for testing different viewport sizes
 * Add ?responsive-test=true to the URL to activate
 */
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.search.includes('responsive-test=true')) {
        // Create the viewport indicator
        const indicator = document.createElement('div');
        indicator.style.position = 'fixed';
        indicator.style.bottom = '20px';
        indicator.style.right = '20px';
        indicator.style.padding = '10px';
        indicator.style.background = 'rgba(0,0,0,0.7)';
        indicator.style.color = 'white';
        indicator.style.borderRadius = '5px';
        indicator.style.zIndex = '9999';
        indicator.style.fontSize = '14px';
        document.body.appendChild(indicator);
        
        // Create breakpoint toolbar
        const toolbar = document.createElement('div');
        toolbar.style.position = 'fixed';
        toolbar.style.top = '0';
        toolbar.style.left = '0';
        toolbar.style.right = '0';
        toolbar.style.padding = '10px';
        toolbar.style.background = 'rgba(0,0,0,0.7)';
        toolbar.style.color = 'white';
        toolbar.style.zIndex = '9999';
        toolbar.style.display = 'flex';
        toolbar.style.justifyContent = 'center';
        toolbar.style.gap = '10px';
        document.body.appendChild(toolbar);
        
        // Add breakpoint buttons
        const breakpoints = [
            {name: 'XS', width: 375},
            {name: 'SM', width: 640},
            {name: 'MD', width: 768},
            {name: 'LG', width: 1024},
            {name: 'XL', width: 1280},
            {name: '2XL', width: 1536}
        ];
        
        breakpoints.forEach(breakpoint => {
            const button = document.createElement('button');
            button.textContent = breakpoint.name;
            button.style.padding = '5px 10px';
            button.style.border = 'none';
            button.style.borderRadius = '3px';
            button.style.cursor = 'pointer';
            
            button.addEventListener('click', function() {
                window.resizeTo(breakpoint.width, window.innerHeight);
            });
            
            toolbar.appendChild(button);
        });
        
        // Update indicator on resize
        function updateIndicator() {
            const width = window.innerWidth;
            let currentBreakpoint = 'XS';
            
            if (width >= 1536) currentBreakpoint = '2XL';
            else if (width >= 1280) currentBreakpoint = 'XL';
            else if (width >= 1024) currentBreakpoint = 'LG';
            else if (width >= 768) currentBreakpoint = 'MD';
            else if (width >= 640) currentBreakpoint = 'SM';
            
            indicator.textContent = `${width}px (${currentBreakpoint})`;
        }
        
        window.addEventListener('resize', updateIndicator);
        updateIndicator(); // Initial update
    }
});