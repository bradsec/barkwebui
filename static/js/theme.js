document.addEventListener('DOMContentLoaded', () => {
    const themeSwitcher = document.getElementById('theme-switcher');

    function setTheme(theme) {
        const body = document.body;
        const themeColorMeta = document.querySelector('meta[name="theme-color"]');
        const sunIcon = document.getElementById('sun-icon');
        const moonIcon = document.getElementById('moon-icon');
    
        if (theme === 'dark') {
            body.setAttribute('data-theme', 'dark');
            themeColorMeta.content = "#202020";
            sunIcon.style.display = "none";
            moonIcon.style.display = "block";
        } else {
            body.removeAttribute('data-theme');
            themeColorMeta.content = "#FFFFFF";
            sunIcon.style.display = "block";
            moonIcon.style.display = "none";
        }
    }    
  
    // Load saved theme from local storage
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      setTheme(savedTheme);
    } else {
      setTheme('light');
    }
  
    themeSwitcher.addEventListener('click', () => {
      const body = document.body;
      const currentTheme = body.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      setTheme(newTheme);
      localStorage.setItem('theme', newTheme);
    });
});
