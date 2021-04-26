var _requestAnimationFrame = (function() {
	if (typeof window !== 'undefined' && 'requestAnimationFrame' in window)
		return function(callback) {
			window.requestAnimationFrame(callback);
		};
	else {
		var timeout = null;
		return function(callback) {
			clearTimeout(timeout);
			timeout = setTimeout(callback, 10);
		};
	}
})();

(function (exports) {

function set(obj, path, value) {
	const steps = path.split('.');
	while (steps.length > 1) {
		const step = steps.shift();
		if (step in obj)
			obj = obj[step]
		else
			throw new Error('object has no property ' + step);
	}
	return obj[steps[0]] = value;
}

function sqr(x) { return x * x }

function dist2(v, w) { return sqr(v.x - w.x) + sqr(v.y - w.y) }

function distToSegmentSquared(p, v, w) {
	const l2 = dist2(v, w);

	if (l2 == 0)
		return dist2(p, v);

	let t = ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2;
	t = Math.max(0, Math.min(1, t));

	return dist2(p, {
		x: v.x + t * (w.x - v.x),
		y: v.y + t * (w.y - v.y)
	});
}

function distToSegment(p, v, w) {
	return Math.sqrt(distToSegmentSquared(p, v, w));
}

function min(a, b) {
	if (a === undefined || isNaN(a))
		return b;
	if (b === undefined || isNaN(b))
		return a;
	return Math.min(a, b);
}

function max(a, b) {
	if (a === undefined || isNaN(a))
		return b;
	if (b === undefined || isNaN(b))
		return a;
	return Math.max(a, b);
}

class Bounds {
	constructor(x, y, width, height) {
		this.x = x;
		this.y = y;
		this.width = width;
		this.height = height;
	}

	get center() {
		return {
			x: this.x + 0.5 * this.width,
			y: this.y + 0.5 * this.height
		};
	}

	including(box) {
		let minX = min(this.x, box.x);
		let minY = min(this.y, box.y);
		let maxX = max(this.x + this.width, box.x + box.width);
		let maxY = max(this.y + this.height, box.y + box.height);
		return new Bounds(minX, minY, maxX - minX, maxY - minY);
	}

	pad(x, y) {
		return new Bounds(this.x - x, this.y - y, this.width + 2 * x, this.height + 2 * y);
	}
}

class Claim {
	constructor(graph, text, data) {
		this.graph = graph;
		this._text = text;
		this.data = data || {};
		this.ax = 0;
		this.ay = 0;
		this.dx = 0;
		this.dy = 0;
		this.width = null;
		this.height = null;
	}

	setPosition(x, y) {
		this.ax = x;
		this.ay = y;
	}
	
	delete() {
		// Remove the claims from the graph
		this.graph.claims = this.graph.claims.filter(claim => claim !== this);

		// Also from the current selection
		this.graph.selectedClaims = this.graph.selectedClaims.filter(claim => claim !== this);

		// And delete any of the relations that are connected to this claim
		this.graph.relations.forEach(relation => {
			if (relation.claim === this || relation.target === this)
				relation.delete();
		});
	}

	set text(text) {
		this._text = text;
		this.lines = null;
		this.width = null;
		this.height = null;
	}

	get text() {
		return this._text;
	}
	
	get x() {
		return this.ax + this.dx;
	}
	
	get y() {
		return this.ay + this.dy;
	}

	get center() {
		return {
			x: this.x + 0.5 * this.width,
			y: this.y + 0.5 * this.height
		};
	}
}

class Relation {
	constructor(graph, claim, target, type, data) {
		this.graph = graph;
		this.claim = claim;
		this.target = target;
		this.type = type;
		this.data = data || {};
	}

	static get SUPPORT() {
		return 'support';
	}

	static get ATTACK() {
		return 'attack';
	}

	static get CONDITION() {
		return 'warrant';
	}

	static get EXCEPTION() {
		return 'undercut';
	}

	delete() {
		// And also delete any relation that targets this relation
		this.graph.relations.forEach(relation => {
			if (relation.target === this)
				relation.delete();
		});

		// Delete the relation from the graph
		this.graph.relations = this.graph.relations.filter(relation => relation !== this);

		// Also filter it out of the selected relations
		this.graph.selectedRelations = this.graph.selectedRelations.filter(relation => relation !== this);
	}

	get x() {
		return this.claim.x + (this.target.x - this.claim.x) / 2;
	}
	
	get y() {
		return this.claim.y + (this.target.y - this.claim.y) / 2;
	}
	
	get width() {
		return 1;
	}
	
	get height() {
		return 1;
	}
	
	get center() {
		return {
			x: this.claim.center.x + (this.target.center.x - this.claim.center.x) / 2,
			y: this.claim.center.y + (this.target.center.y - this.claim.center.y) / 2
		};
	}

	joint(i, n) {
		return new Bounds(
			this.claim.center.x + (i + 1) * (this.target.center.x - this.claim.center.x) / (n + 1),
			this.claim.center.y + (i + 1) * (this.target.center.y - this.claim.center.y) / (n + 1),
			0, 0);
	}
};


function typerepr(obj)
{
	if (obj === undefined)
		return 'undefined';
	if (obj === null)
		return 'null';
	if (obj.constructor)
		return obj.constructor.name;
	return typeof obj;
}


class LetterSequence {
	constructor() {
		this.counter = 0;
	}

	next() {
		let val = this.toString();
		++this.counter;
		return val;
	}

	toString() {
		let value = this.counter;
		let chars = '';
		
		if (value === 0) {
			return 'a';
		}

		while (value > 0) {
			chars = ((value % 26) + 10).toString(36) + chars;
			value = Math.floor(value / 26);
		}

		return chars;
	}
}


class Graph {
	constructor(canvas) {
		this.canvas = canvas;

		this.context = this.canvas.getContext('2d');

		this.claims = [];
		this.relations = [];

		this.selectedClaims = [];
		this.selectedRelations = [];

		this.dragStartPosition = null;
		this.wasDragging = false;
		this.cursor = null;
		this.elementUnderCursor = null;

		this.listeners = {
			'draw': [],
			'drop': [],
			'mouseover': [],
			'mouseout': [],
			'click': []
		};

		if ('addEventListener' in this.canvas) {
			this.canvas.tabIndex = -1;
			this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this));
			this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
			this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this));
			this.canvas.addEventListener('mouseout', this.onMouseOut.bind(this));
			this.canvas.addEventListener('dblclick', this.onDoubleClick.bind(this));
			this.canvas.addEventListener('keydown', this.onKeyDown.bind(this));
			this.canvas.addEventListener('keyup', this.onKeyUp.bind(this));
			this.canvas.addEventListener('focus', this.update.bind(this));
			this.canvas.addEventListener('blur', this.update.bind(this));
		}

		const scopeStyles = {};

		const colours = [
			"#ff0000", "#ffee00", "#5395a6", "#40002b", "#f20000", "#7f7920",
			"#6c98d9", "#d9a3bf", "#e58273", "#807d60", "#3d3df2", "#ff408c",
			"#ff8c40", "#5ccc33", "#110080", "#8c2331", "#e6c3ac", "#004d29",
			"#282633", "#593c00", "#00bf99", "#b32daa"
		];

		this.style = {
			scale: typeof window !== 'undefined' && 'devicePixelRatio' in window ? window.devicePixelRatio : 1.0,
			padding: {
				top: 20,
				right: 20,
				bottom: 20,
				left: 20
			},
			claim: {
				padding: {
					top: 3,
					left: 10,
					bottom: 10,
					right: 10
				},
				fontSize: 13,
				lineHeight: 16,
				maxWidth: 300,
				background: function(claim) {
					return 'white';
				},
				fontColor: function(claim) {
					return claim.data.assumption ? '#ccc' : 'black';
				},
				fontStyle: function(claim) {
					return claim.data.assumption ? 'italic' : '';
				},
				border: function(claim) {
					if (claim.data.scope) {
						if (!(claim.data.scope in scopeStyles))
							scopeStyles[claim.data.scope] = colours.pop();
						
						return scopeStyles[claim.data.scope];
					}

					return claim.data.assumption ? '#ccc' : 'black';
				}
			},
			relation: {
				size: 5,
				color: function(relation) {
					return relation.data.assumption ? '#ccc' : 'black';
				},
				dash: function(relation) {
					return relation.type === Relation.CONDITION || relation.type === Relation.EXCEPTION ? [5, 5] : [];
				}
			}
		};

		// this.input = document.createElement('input');
		// this.input.type = 'text';
		// this.input.style.position = 'absolute';
		// this.input.style.display = 'none';
		// this.canvas.parentNode.appendChild(this.input);

		if (typeof window !== 'undefined' && 'addEventListener' in window)
			window.addEventListener('resize', this.resize.bind(this));

		this.updateCanvasSize();
	}

	addClaim(text, data) {
		const claim = new Claim(this, text, data);
		this.claims.push(claim);
		this.update();
		return claim;
	}

	addRelation(claim, target, type, data) {
		if (Array.isArray(claim)) {
			if (claim.length === 0) {
				throw new Error('No source claims provided');
			}
			else if (claim.length > 1) {
				// We need a compound statement to merge stuff
				const compound = this.addClaim('&', {compound: true});

				claim.forEach(claim => {
					this.addRelation(claim, compound, type, data);
				});

				return this.addRelation(compound, target, type, Object.assign({}, data, {merged: true}));
			}
			else {
				// Treat it as a single argument
				claim = claim[0];
			}
		}

		if (!(claim instanceof Claim))
			throw new TypeError('Claim should be instance of Claim, is ' + typerepr(target));

		if (!(target instanceof Claim) && !(target instanceof Relation))
			throw new TypeError('Target should be instance of Claim or Relation, is ' + typerepr(target));

		const relation = new Relation(this, claim, target, type, data);
		this.relations.push(relation);
		this.update();

		return relation;
	}

	findRootClaims() {
		if (this.claims.length == 0)
			return [];
		
		// Find all claims that are the source for a relation
		const sources = this.relations.map(relation => relation.claim);

		// Now filter from all known claims those source claims
		const roots = this.claims.filter(claim => sources.indexOf(claim) === -1);

		// and we should be left with the roots
		// (which are only attacked or supported, or neither)
		if (roots.length > 0)
			return roots;

		// Oh crap, only circular claims. Great! Let's just take the first one added.
		return [this.claims[0]];
	}

	findRelations(criteria) {
		// You can pass in an array of conditions to get the joined set, for example
		// when you pass in [{claim: x}, {target: x}], you get all relations that
		// have either the claim or the target as x. When you pass in [{claim: x, target: x}]
		// you only get the relations that have both X as the claim and target at the same time.

		if (!Array.isArray(criteria))
			criteria = [criteria];

		function test(relation) {
			return criteria.some(condition => {
				return (!('claim' in condition) || relation.claim === condition.claim)
					&& (!('target' in condition) || relation.target === condition.target)
					&& (!('type' in condition || relation.type === condition.type));
			});
		};

		return this.relations.filter(test);
	}

	findContext(claim) {
		// The context of a claim is all its conditions and exceptions
		const types = [Relation.CONDITION, Relation.EXCEPTION];

		const context = [claim];

		for (let i = 0; i < context.length; ++i) {
			const relations = this.findRelations({target: context[i]});

			relations.forEach(relation => {
				if (!types.includes(relation.type))
					return;

				if (!context.includes(relation))
					context.push(relation);

				if (!context.includes(relation.claim))
					context.push(relation.claim);
			});
		}

		return context.filter(obj => obj instanceof Claim);
	}

	findClaimAtPosition(pos) {
		return this.claims.find(claim => {
			return pos.x > claim.x
				&& pos.y > claim.y
				&& pos.x < claim.x + claim.width
				&& pos.y < claim.y + claim.height;
		});
	}

	findRelationAtPosition(pos, buffer){
		return this.relations.find(relation => {
			let target = relation.target;
			let claim = relation.claim;

			if (relation.type === Relation.SUPPORT || relation.type === Relation.ATTACK) {
				target = this.getContextBox(target);
				claim = this.getContextBox(claim);
			}

			return distToSegment(pos, claim.center, target.center) <= buffer;
		});
	}

	onMouseDown(e) {
		this.wasDragging = false;

		this.dragStartPosition = {
			x: e.offsetX,
			y: e.offsetY
		};

		const cursor = {
			x: e.offsetX - this.style.padding.left,
			y: e.offsetY - this.style.padding.top,
		};

		if (e.altKey)
			return;

		const claim = this.findClaimAtPosition(cursor);

		if (claim) {
			if (!this.selectedClaims.includes(claim)) {
				if (e.shiftKey) {
					this.selectedClaims.push(claim);
				} else {
					this.selectedClaims = [claim];
					this.selectedRelations = [];
				}

				this.update();
			}

			return;
		}

		const relation = this.findRelationAtPosition(cursor, 5);

		if (relation) {
			if (!this.selectedRelations.includes(relation)) {
				if (e.shiftKey) {
					this.selectedRelations.push(relation);
				} else {
					this.selectedRelations = [relation];
					this.selectedClaims = [];
				}

				this.update();
			}
		}
	}

	onDoubleClick(e) {
		const cursor = {
			x: e.offsetX - this.style.padding.left,
			y: e.offsetY - this.style.padding.top,
		};

		let claim = this.findClaimAtPosition(cursor);
		
		const text = prompt('Text of claim:', claim ? claim.text : '');

		if (!text)
			return;

		if (!claim) {
			claim = this.addClaim(text);
			claim.setPosition(cursor.x, cursor.y);
		} else {
			claim.text = text;
		}
	}

	onMouseMove(e) {
		if (this.dragStartPosition === null) {
			const cursor = {
				x: e.offsetX - this.style.padding.left,
				y: e.offsetY - this.style.padding.top,
			};

			const elementUnderCursor = this.findClaimAtPosition(cursor) || this.findRelationAtPosition(cursor, 5);

			if (elementUnderCursor)
				this.canvas.style.cursor = 'pointer';
			else
				this.canvas.style.cursor = 'default';

			if (this.elementUnderCursor !== elementUnderCursor) {
				if (this.elementUnderCursor)
					this.fire('mouseout', {target: this.elementUnderCursor})
				if (elementUnderCursor)
					this.fire('mouseover', {target: elementUnderCursor});

				this.elementUnderCursor = elementUnderCursor;
			}

			if (e.altKey) {
				this.cursor = {
					x: cursor.x,
					y: cursor.y,
					type: e.shiftKey ? Relation.ATTACK : Relation.SUPPORT
				};
				
				this.update();
			}
		} else {
			const delta = {
				x: e.offsetX - this.dragStartPosition.x,
				y: e.offsetY - this.dragStartPosition.y
			};

			// If we have been dragging a bit, cancel the onClick
			if (Math.abs(delta.x) > 2 || Math.abs(delta.y) > 2)
				this.wasDragging = true;

			this.selectedClaims.forEach(claim => {
				claim.dx = delta.x;
				claim.dy = delta.y;
			});

			this.update();
		}
	}

	onMouseUp(e) {
		e.preventDefault();

		this.canvas.style.cursor = 'default';

		const cursor = {
			x: e.offsetX - this.style.padding.left,
			y: e.offsetY - this.style.padding.top,
		};

		if (!this.wasDragging) {
			const claim = this.findClaimAtPosition(cursor);
			const relation = claim ? null : this.findRelationAtPosition(cursor, 5);

			if (e.altKey) {
				if (this.selectedClaims.length > 0) {
					if (claim) {
						this.addRelation(
							this.selectedClaims[0],
							claim,
							e.shiftKey ? Relation.ATTACK : Relation.SUPPORT);
					} else if (relation) {
						this.addRelation(
							this.selectedClaims[0],
							relation,
							e.shiftKey ? Relation.ATTACK : Relation.SUPPORT);
					}
				}
			} else {
				if (claim || relation) {
					this.fire('click', {target: claim || relation})
				} else {
					if (this.selectedClaims.length != 0 || this.selectedRelations.length != 0) {
						this.selectedClaims = [];
						this.selectedRelations = [];
						this.update();
					}
				}
			}
		}
		else if (this.selectedClaims.length > 0) {
			this.selectedClaims.forEach(claim => {
				claim.ax += claim.dx;
				claim.ay += claim.dy;
				claim.dx = 0;
				claim.dy = 0;
			});

			this.fire('drop');
		}
		
		this.dragStartPosition = null;
	}

	onMouseOut(e) {
		if (this.cursor) {
			this.cursor = null;
			this.update();
		}
	}

	onKeyDown(e) {
		const stepSize = 2 * this.style.scale;

		switch (e.keyCode) {
			case 8: // Backspace
			case 46: // Delete
				this.selectedClaims.forEach(claim => claim.delete());
				this.selectedRelations.forEach(relation => relation.delete());
				e.preventDefault();
				this.update();
				break;

			case 9: // Capture [tab] key
				// If there are no claims, there is nothing to move focus to
				if (this.claims.length === 0)
					return;

				const direction = e.shiftKey ? -1 : 1;
				let idx = -1;
				
				// Find the first claim in selectedClaims
				if (this.selectedClaims.length > 0)
					idx = this.claims.indexOf(this.selectedClaims[0]);

				if (idx < this.claims.length - 1)
					this.selectedClaims = [this.claims[(this.claims.length + idx + direction) % this.claims.length]];
				else
					this.selectedClaims = [];

				e.preventDefault();
				this.update();
				break;

			case 40: // down
				this.selectedClaims.forEach(claim => {
					claim.ay += stepSize;
				});
				e.preventDefault();
				this.update();
				break;

			case 38: // up
				this.selectedClaims.forEach(claim => {
					claim.ay -= stepSize;
				});
				e.preventDefault();
				this.update();
				break;

			case 37: // left
				this.selectedClaims.forEach(claim => {
					claim.ax -= stepSize;
				});
				e.preventDefault();
				this.update();
				break;

			case 39: // right
				this.selectedClaims.forEach(claim => {
					claim.ax += stepSize;
				});
				e.preventDefault();
				this.update();
				break;

			case 16: // Shift
			case 18: // Alt
				this.update();
				break;
		}
	}

	onKeyUp(e) {
		switch (e.keyCode) {
			case 16: // Shift
			case 18: // Alt
				this.cursor = null;
				this.update();
				break;
		}
	}

	on(eventName, callback) {
		this.listeners[eventName].push(callback);
	}

	off(eventName, callback) {
		this.listeners[eventName] = this.listeners[eventName].filter(registeredCallback => callback !== registeredCallback);
	}

	fire(eventName, event) {
		this.listeners[eventName].forEach(callback => callback(event));
	}

	resize() {
		_requestAnimationFrame(this.draw.bind(this));
	}

	fit() {
		// Find initial offsets
		const startX = this.claims.map(claim => claim.x).min();
		const startY = this.claims.map(claim => claim.y).min();

		// Remove that empty offset
		this.claims.forEach(claim => {
			claim.setPosition(
				claim.x - startX,
				claim.y - startY);
		});

		this.resize();
	}

	fitVertically() {
		// Find initial offsets
		const startY = this.claims.map(claim => claim.y).min();

		// Remove that empty offset
		this.claims.forEach(claim => {
			claim.setPosition(
				claim.x,
				claim.y - startY + this.style.scale);
		});

		// Find outer limits
		const height = this.claims.map(claim => claim.y + claim.height).max();

		this.resize();
	}

	destroy() {
		this.canvas.parentNode.removeChild(this.canvas);
	}

	updateCanvasSize(e) {
		const width = this.style.padding.left + this.style.padding.right + this.claims.map(claim => claim.x + claim.width).max();
		const height = this.style.padding.top + this.style.padding.bottom + this.claims.map(claim => claim.y + claim.height).max();

		this.canvas.width = this.style.scale * width;
		this.canvas.height = this.style.scale * height;

		if ('style' in this.canvas) {
			this.canvas.style.width = width + 'px';
			this.canvas.style.height = height + 'px';
		}
	}

	updateClaimSizes() {
		this.context.font = (this.style.scale * this.style.claim.fontSize) + 'px sans-serif';

		this.claims.forEach(claim => {
			if (!Array.isArray(claim.lines))
				claim.lines = this.context.wrapText(claim.text, this.style.claim.maxWidth);

			if (claim.width === null || claim.height === null) {
				if (claim.data.compound) {
					claim.width = 0;
					claim.height = 0;
				} else {
					let textWidth = claim.lines.map(line => this.context.measureText(line).width).max();
					claim.width = textWidth / this.style.scale + this.style.claim.padding.left + this.style.claim.padding.right;
					claim.height = claim.lines.length * this.style.claim.lineHeight + this.style.claim.padding.top + this.style.claim.padding.bottom;
				}
			}
		});
	}

	update() {
		_requestAnimationFrame(this.draw.bind(this));
	}

	draw() {
		// Update the size of all the claim boxes
		this.updateClaimSizes();

		// Make sure all the boxes will fit inside the canvas
		this.updateCanvasSize();

		// Clear the canvas
		this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);

		// Translate for the padding (simplifies drawing commands immensely)
		this.context.translate(
			this.style.padding.left * this.style.scale,
			this.style.padding.top * this.style.scale);

		this.context.strokeStyle = '#000';
		this.context.fillStyle = 'black';
		this.context.lineWidth = this.style.scale * 1;

		this.drawContexts();

		this.drawRelations();

		this.drawClaims();

		this.drawSelection();

		this.drawCursor();
		
		this.fire('draw');
		
		// Undo the translation
		this.context.setTransform(1, 0, 0, 1, 0, 0);
	}

	getContextBox(object)
	{
		if (!(object instanceof Claim))
			return object;

		if (object.data.compound)
			return object;

		const padding = 5;

		const context = this.findContext(object);

		if (context.length === 1)
			return object;

		return context.reduce((bounds, claim) => bounds.including(claim), new Bounds()).pad(padding, padding);
	}

	drawContexts()
	{
		const ctx = this.context;

		this.claims.forEach(claim => {
			const bounds = this.getContextBox(claim);

			if (bounds === claim)
				return;

			if (this.findRelations({claim: claim}).length === 0)
				return;
			
			ctx.fillStyle = 'white';
			ctx.fillRect(
				this.style.scale * bounds.x,
				this.style.scale * bounds.y,
				this.style.scale * bounds.width,
				this.style.scale * bounds.height);

			ctx.strokeStyle = 'black';
			ctx.setLineDash([5, 5]);
			ctx.lineWidth = this.style.scale * 1;
			ctx.strokeRect(
				this.style.scale * bounds.x,
				this.style.scale * bounds.y,
				this.style.scale * bounds.width,
				this.style.scale * bounds.height);
		});
	}

	drawClaims()
	{
		var ctx = this.context,
			padding = this.style.claim.padding,
			scale = this.style.scale,
			claimColor = this.style.claim.background,
			claimBorder = this.style.claim.border,
			fontColor = this.style.claim.fontColor,
			fontSize = this.style.claim.fontSize,
			fontStyle = this.style.claim.fontStyle,
			lineHeight = this.style.claim.lineHeight;

		// Sort claims with last selected drawn last (on top)
		this.claims.slice().sort((a, b) => this.selectedClaims.indexOf(a) - this.selectedClaims.indexOf(b));

		ctx.setLineDash([]);

		// Draw all claims
		this.claims.forEach(claim => {
			if (claim.data.compound)
				return;

			// Draw the background
			ctx.fillStyle = claimColor(claim);
			ctx.fillRect(
				scale * claim.x,
				scale * claim.y,
				scale * claim.width,
				scale * claim.height);

			// Draw the border
			ctx.strokeStyle = claimBorder(claim);
			ctx.lineWidth = scale * 1;
			ctx.strokeRect(
				scale * claim.x,
				scale * claim.y,
				scale * claim.width,
				scale * claim.height);

			// Set the font
			ctx.font = [fontStyle(claim), (scale * fontSize) + 'px','sans-serif'].join(' ');

			// Draw the inner text
			ctx.fillStyle = fontColor(claim);
			claim.lines.forEach(function(line, i) {
				ctx.fillText(line,
					scale * (claim.x + padding.left),
					scale * (claim.y + padding.top + (i + 1) * lineHeight));
			});
		});
	}

	drawSelection()
	{
		const ctx = this.context;
		const scale = this.style.scale;
		const color = typeof document !== 'undefined' && document.activeElement == this.canvas ? 'blue' : 'gray';

		ctx.lineWidth = scale * 3;
		ctx.strokeStyle = color;
		
		// Draw an extra outline for the selected claims
		this.selectedClaims.forEach(claim => {
			ctx.strokeRect(
				scale * (claim.x - 2),
				scale * (claim.y - 2),
				scale * (claim.width + 4),
				scale * (claim.height + 4));
		});

		this.selectedRelations.forEach(relation => {
			let target = relation.target;
			let claim = relation.claim;

			if (relation.type === Relation.SUPPORT || relation.type === Relation.ATTACK) {
				target = this.getContextBox(target);
				claim = this.getContextBox(claim);
			}

			const s = this.offsetPosition(target, claim);
			const t = this.offsetPosition(claim, target);
			ctx.lineWidth = scale * 3;
			ctx.strokeStyle = color;
			this.drawRelationLine(s, t, relation.type);
		});
	}

	drawRelations()
	{
		const ctx = this.context;

		// Draw all the relation arrows
		this.relations.forEach(relation => {
			// Offset the target position of the line a bit towards the border. So that
			// when drawing an arrow, we draw it towards the border, and not the center
			// where it will be behind the actual box.

			let target = relation.target;
			let source = relation.claim;

			// Support and attack relations are drawn from context to context
			if ([Relation.SUPPORT, Relation.ATTACK].includes(relation.type)) {
				target = this.getContextBox(target);
				source = this.getContextBox(source);
			}

			if (relation.target instanceof Relation) {
				const incoming = this.findRelations({target: relation.target}).reverse();
				const index = incoming.indexOf(relation);
				target = relation.target.joint(index, incoming.length);
			}
			
			const s = this.offsetPosition(target, source);
			const t = this.offsetPosition(source, target);

			const color = this.style.relation.color(relation);
			ctx.strokeStyle = color;
			ctx.fillStyle = color;

			ctx.setLineDash(this.style.relation.dash(relation));

			ctx.lineWidth = this.style.scale * 1;

			this.drawRelationLine(s, t, relation.target.data.compound ? null : relation.type);
		});
	}

	drawRelationLine(s, t, type)
	{
		const ctx = this.context,
			scale = this.style.scale,
			arrowRadius = this.style.relation.size;

		ctx.save();

		ctx.beginPath();
		ctx.moveTo(scale * s.x, scale * s.y);

		// To almost the target (but a bit less)
		const angle = Math.atan2(
			t.y - s.y,
			t.x - s.x);

		switch (type) {
			case Relation.SUPPORT:
			case Relation.CONDITION:
				ctx.lineTo(
					scale * t.x - scale * arrowRadius * Math.cos(angle),
					scale * t.y - scale * arrowRadius * Math.sin(angle));
				ctx.stroke();

				if (type === Relation.SUPPORT)
					ctx.lineWidth = scale * 2;
				else
					ctx.lineWidth = scale * 1;
			
				ctx.setLineDash([]);
				ctx.arrow(scale * arrowRadius, 
					scale * s.x,
					scale * s.y,
					scale * t.x,
					scale * t.y);

				if (type === Relation.SUPPORT)
					ctx.fill();
				else
					ctx.stroke();
				break;

			case Relation.ATTACK:
			case Relation.EXCEPTION:
				ctx.lineTo(
					scale * t.x - scale * arrowRadius * Math.cos(angle),
					scale * t.y - scale * arrowRadius * Math.sin(angle));
				ctx.stroke();

				if (type === Relation.ATTACK)
					ctx.lineWidth = scale * 2;
				else
					ctx.lineWidth = scale * 1;

				ctx.setLineDash([]);
				ctx.cross(0.75 * scale * arrowRadius, 
					scale * s.x,
					scale * s.y,
					scale * t.x,
					scale * t.y);
				ctx.stroke();
				break;

			default:
				ctx.lineTo(
					scale * t.x,
					scale * t.y);
				ctx.stroke();
				break;
		}

		ctx.restore();
	}

	drawCursor()
	{
		if (!this.cursor || this.selectedClaims.length === 0)
			return;

		const ctx = this.context;
		const relationColor = this.style.relation.color;
		const claim = this.selectedClaims[0];

		const snapTarget = this.findClaimAtPosition(this.cursor, 5) || this.findRelationAtPosition(this.cursor, 5);

		ctx.lineWidth = this.style.scale * 1;
		this.drawRelationLine(
			this.offsetPosition(snapTarget ? snapTarget : {center: this.cursor}, claim),
			snapTarget ? this.offsetPosition(claim, snapTarget) : this.cursor,
			this.cursor.type);
	}

	offsetPosition(sourceBox, targetBox)
	{
		function center(box) {
			return {
				x: box.center.x,
				y: box.center.y,
				width: box.width,
				height: box.height
			};
		}

		const source = center(sourceBox);
		const target = center(targetBox);

		if (target.width === 0 || target.height === 0)
			return {x: target.x, y: target.y};

		const D = {
			x: source.x - target.x,
			y: source.y - target.y
		};

		let t = {
			x: target.x + (target.x > source.x ? -0.5 : 0.5) * target.width,
			y: target.y + (D.y / D.x) * (target.x > source.x ? -0.5 : 0.5) * target.width
		};

		// console.log(
		// 	D.x / D.y * target.height < -0.5 * target.width,
		// 	D.y / D.x * target.width < -0.5 * target.height
		// );

		if ((D.x / D.y < target.width / target.height)
			&& !(D.x / D.y * target.height < -0.5 * target.width))
			t = {
				x: target.x + (D.x / D.y) * (target.y > source.y ? -0.5 : 0.5) * target.height,
				y: target.y + (target.y > source.y ? -0.5 : 0.5) * target.height
			};

		return t;
	}

	parse(input)
	{
		const variables = {};

		const lines = Array.isArray(input) ? input : input.split(/\r?\n/);

		const rules = [
			{
				pattern: /^\s*([a-z0-9]+)\s*:\s*(?:(assume)\s+)?((?:[a-z0-9]+\s+)+)(?:(support|attack|warrant|undercut)s)\s+([a-z0-9]+)$/,
				processor: match => {
					let sources = match[3].split(/\s+/).filter(name => name != '').map(name => {
						if (!(name in variables))
							throw new Error('Variable "' + name + '" is unknown');
						return variables[name];
					});
					let target = variables[match[5]];
					let relation = this.addRelation(sources, target, match[4], {variable: match[1], assumption: match[2] == 'assume'});
					variables[match[1]] = relation;
				}
			},
			{
				pattern: /^\s*([a-z0-9]+)\s*:\s*(?:(assume)\s+)?(.+?)\s*$/,
				processor: match => {
					variables[match[1]] = this.addClaim(match[3], {variable: match[1], assumption: match[2] == 'assume'});
				}
			},
			{
				pattern: /^\s*style\s+([a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*)\s+(\d*(?:\.\d+)?)\s*$/,
				processor: match => {
					try {
						set(this.style, match[1], parseFloat(match[2]));
					} catch(e) {
						console.warn('Cannot set style property ' + match[1], e);
					}
				}
			},
			{
				pattern: /^\s*position\s+([a-z0-9]+)\s+at\s+(-?\d+)\s+(-?\d+)\s*$/,
				processor: match => {
					variables[match[1]].setPosition(parseInt(match[2]), parseInt(match[3]));
				}
			}
		];

		lines.filter(line => line.trim() !== '').forEach((line, index) => {
			for (const rule of rules) {
				try {
					let match = line.match(rule.pattern);
					if (match)
						return rule.processor(match, line);
				} catch (e) {
					throw new Error('Parse error on line ' + (index + 1) + ': ' + e.message);
				}
			}

			throw new Error('Parse error on line ' + (index + 1) + ': unknown instruction "' + line + '"');
		});
	}

	toString() {
		const variables = new LetterSequence();

		const mapping = new Map();

		const lines = [];

		const positions = [];

		this.claims.forEach(claim => {
			// Skip the compound nodes
			if (claim.data.compound)
				return;

			let variable = variables.next();

			let line = [variable + ':'];

			mapping.set(claim, variable);

			if (claim.data.assumption)
				line.push('assume');

			line.push(claim.text);

			lines.push(line.join(' '));

			positions.push(['position', variable, 'at', Math.round(claim.x), Math.round(claim.y)].join(' '));
		});

		this.relations.forEach(relation => {
			// Skip the relations that link to compound nodes.
			// We handle those at the compound nodes.
			if (relation.target.data.compound)
				return;

			let variable = variables.next();

			let line = [variable + ':'];

			// Save the variable for later references
			mapping.set(relation, variable);

			// Find the sources: If it is a merged relation, go
			// to the relations that link to the originating
			// compound claim and get their origin. Otherwise
			// just get the origin of the relation.
			let sources = relation.data.merged
				? this.relations
					.filter(rel => rel.target === relation.claim)
					.map(rel => rel.claim)
				: [relation.claim];
			
			// If either the original relation is an assumption, or
			// it is a merged relation and all sources are assumptions,
			// this relation will be marked as an assumption.
			if (relation.data.assumption || relation.data.merged && sources.filter(rel => !rel.data.assumption).length == 0)
				line.push('assume');

			// Add all the variables of the sources
			line.push.apply(line, sources.map((source) => mapping.get(source)));

			// Add the type
			line.push(relation.type + 's');

			// Add the target
			line.push(mapping.get(relation.target));

			// Done!
			lines.push(line.join(' '));
		});

		Array.prototype.push.apply(lines, positions);

		return lines.join("\n");
	}
}

// Set default claim class
Graph.Claim = Claim; 

exports.Claim = Claim;
exports.Relation = Relation;
exports.Graph = Graph;
exports.Bounds = Bounds;

})(typeof exports !== 'undefined' ? exports : window);
