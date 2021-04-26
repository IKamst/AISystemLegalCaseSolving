class TabPanel {
	constructor(root) {
		this.shadow = root;

		this.labelContainer = root.querySelector('.tab-list') || document.createElement('ol');
		this.labelContainer.classList.add('tab-list');
		this.shadow.appendChild(this.labelContainer);

		this.panelContainer = root.querySelector('.panel-container') || document.createElement('div');
		this.panelContainer.classList.add('panel-container');
		this.shadow.appendChild(this.panelContainer);

		this.tabs = [];

		this.counter = 0;
	}

	createTab(name) {
		let tab = {};

		tab.id = ++this.counter;

		tab.panel = document.createElement('div');

		tab.label = document.createElement('li');
		tab.label.dataset.tabId = tab.id;
		
		tab.labelText = document.createElement('span');
		tab.labelText.tabIndex = 0;
		tab.labelText.textContent = name;

		tab.closeButton = document.createElement('button');
		tab.closeButton.className = 'close-button';
		tab.closeButton.innerHTML = '&times;';

		tab.labelText.addEventListener('focus', e => {
			this.selectedTab = tab;
		});

		tab.closeButton.addEventListener('click', e => {
			this.removeTab(tab);
		});

		tab.panel.addEventListener('focusin', e => {
			this.selectedTab = tab;
		});

		tab.label.appendChild(tab.labelText);
		tab.label.appendChild(tab.closeButton);

		this.appendTab(tab);

		return tab.panel;
	}

	appendTab(tab) {
		this.tabs.push(tab);
		this.labelContainer.appendChild(tab.label);
		this.panelContainer.appendChild(tab.panel);

		if (this.tabs.length === 1)
			this.selectedTab = tab;
	}

	removeTab(tab) {
		this.labelContainer.removeChild(tab.label);
		this.panelContainer.removeChild(tab.panel);

		let index = this.tabs.indexOf(tab);
		this.tabs.splice(index, 1);

		if (this.tabs.length > 0)
			this.selectedIndex = Math.max(0, index - 1);
	}

	set selectedTab(selected) {
		this.tabs.forEach(tab => {
			if (tab.panel.getAttribute('selected') == 'true')
				tab.panel.dispatchEvent(new CustomEvent('hide'));

			tab.label.setAttribute('selected', tab == selected);
			tab.panel.setAttribute('selected', tab == selected);

			if (tab == selected) 
				tab.panel.dispatchEvent(new CustomEvent('show'));
		});
	}

	get selectedTab() {
		return this.panelContainer.querySelector('[selected=true]');
	}

	clear() {
		Array.from(this.tabs).forEach(tab => this.removeTab(tab));
	}

	set selectedIndex(index) {
		this.selectedTab = this.tabs[index];
	}

	get selectedIndex() {
		return this.tabs.indexOf(tab => tab.panel.getAttribute('selected'));
	}
};