function showTab(tabId) {
    const tabs = document.querySelectorAll('.tab-content');
    const buttons = document.querySelectorAll('.tab-button');
    
    tabs.forEach(tab => tab.classList.remove('active'));
    buttons.forEach(button => button.classList.remove('active'));
    
    document.getElementById(tabId).classList.add('active');
    const activeButton = Array.from(buttons).find(button => button.getAttribute('data-tab') === tabId);
    if (activeButton) {
        activeButton.classList.add('active');
    }
}
