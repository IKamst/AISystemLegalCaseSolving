(function() {

var patch = (function (Graph) {

Graph.prototype.layout = function()
{
	var graph = this;

	var visited = [];

	function layoutClaim(claim) {
		let incoming = graph.findRelations({target: claim});

		let layout = new Layout(Layout.VERTICAL);

		layout.add(claim);

		if (incoming.length > 0) {
			let relationLayout = new Layout(Layout.HORIZONTAL);
			layout.add(relationLayout);

			relationLayout.addAll(incoming.map(layoutRelation));
		}

		return layout;
	}

	function layoutRelation(relation, i, relations) {
		var layout = new Layout(Layout.VERTICAL, Layout.CENTER);

		let incoming = graph.findRelations({target: relation});

		if (incoming.length > 0) {
			let vl = new Layout(Layout.VERTICAL, Layout.START);
			vl.addAll(incoming.map(layoutRelation));

			let hl = new Layout(Layout.HORIZONTAL);
			if (relations.length > 1 && i % 2 == 0) {
				hl.add(vl);
				hl.add(new Spacer(vl.width + 40, 20)); /* push vl to the left */
			} else {
				hl.add(new Spacer(vl.width + 40, 20)); /* push vl to the right */
				hl.add(vl);
			}

			layout.add(hl);
		} else {
			// layout.add(new Spacer(20, 20));
		}

		if (!visited.includes(relation.claim)) {
			visited.push(relation.claim);
			layout.add(layoutClaim(relation.claim));
		}

		return layout;
	}
	
	// Find all claims that have no outgoing relations, and that thus wouldn't be found
	// by iterating all relations as done by layoutClaim.
	var roots = this.findRootClaims();
	
	var layout = new Layout(Layout.HORIZONTAL);

	// Make sure the claims themselves know how large they are. Could be done after these
	// steps, layout is lazy and only needs to know the dimensions once Layout.apply is called.
	this.updateClaimSizes();

	// Reset visited claims list
	visited = [];

	roots.map(layoutClaim).forEach(layout.add, layout);

	return layout;
}

class Spacer {
	constructor(width, height) {
		this.x = null;
		this.y = null;
		this.width = width;
		this.height = height;
	}

	setPosition(x, y) {
		// no-op

		// ... but setting these anyway for the debug drawing
		this.x = x;
		this.y = y;
	}
};

class Layout {
	constructor(direction, alignment)
	{
		this.direction = direction;
		this.alignment = alignment || Layout.CENTER;
		this.elements = [];
		this.parent = null;
	}

	static get HORIZONTAL() {
		return 1;
	}

	static get VERTICAL() {
		return 2;
	}

	static get START() {
		return 1;
	}

	static get END() {
		return 2;
	}

	static get CENTER() {
		return 3;
	}

	add(box) {
		if (box instanceof Layout)
			box.parent = this;

		this.elements.push(box);
	}

	addAll(boxes) {
		boxes.forEach(this.add, this);
	}

	apply() {
		this.setPosition(20, 20);
	}

	setPosition(x, y) {
		// save x & y for rendering
		this.x = x;
		this.y = y;

		// Then the left to right sweep
		switch (this.direction) {
			case Layout.HORIZONTAL:
				let dx = 0;
				let height = this.height;
				this.elements.forEach(el => {
					switch (this.alignment) {
						case Layout.START:
							el.setPosition(x + dx, y);
							break;
						case Layout.END:
							el.setPosition(x + dx, y + height - el.height);
							break;
						case Layout.CENTER:
							el.setPosition(x + dx, y + (height - el.height) / 2);
							break;
					}

					dx += el.width + this.spacing.horizontal;
				});
				break;

			case Layout.VERTICAL:
				let dy = 0;
				let width = this.width;
				this.elements.forEach(el => {
					switch (this.alignment) {
						case Layout.START:
							el.setPosition(x, y + dy);
							break;
						case Layout.END:
							el.setPosition(x + width - el.width, y + dy);
							break;
						case Layout.CENTER:
							el.setPosition(x + (width - el.width) / 2, y + dy);
							break;
					}

					dy += el.height + this.spacing.vertical;
				});
				break;
		}
	}
	
	drawOutline(graph, depth) {
		var ctx = graph.context,
		    scale = graph.style.scale;

		if (depth === undefined)
			depth = 0;

		ctx.lineWidth = 1 * scale;
		ctx.strokeStyle = this.direction === Layout.HORIZONTAL ? 'red' : 'green';
		
		// Draw an extra outline for the selected claims
		ctx.strokeRect(
			scale * (this.x + 2 * depth),
			scale * (this.y + 2 * depth),
			scale * (this.width - 4 * depth),
			scale * (this.height - 4 * depth));

		this.elements.forEach(function(el) {
			if ('drawOutline' in el)
				el.drawOutline(graph, depth + 1);
		});
	}

	get width() {
		let widths = this.elements.map((el) => el.width);

		switch (this.direction) {
			case Layout.HORIZONTAL:
				// total width of all boxes plus spacing in between
				return widths.sum() + Math.max(this.elements.length - 1, 0) * this.spacing.horizontal;

			case Layout.VERTICAL:
				return widths.max();
		}
	}

	get height() {
		let heights = this.elements.map((el) => el.height);

		switch (this.direction) {
			case Layout.HORIZONTAL:
				return heights.max();

			case Layout.VERTICAL:
				// total heights of all the boxes plus spacing in between
				return heights.sum() + Math.max(this.elements.length - 1, 0) * this.spacing.vertical;
		}
	}

	get descendants() {
		// assert that any element only occurs once in the whole tree
		function extract(layout) {
			return layout.elements.map((el) => (el instanceof Layout) ? extract(el) : [el]).flatten();
		}

		return extract(this);
	}
}

Layout.prototype.spacing = {
	horizontal: 20,
	vertical: 40
};

function OutlinePainter(color) {
	return function(graph, depth) {
		var ctx = graph.context,
		    scale = graph.style.scale;

		if (depth === undefined)
			depth = 0;

		ctx.fillStyle = color;
		
		ctx.fillRect(
			scale * this.x,
			scale * this.y,
			scale * this.width,
			scale * this.height);
	};
}

// Add a few more outline drawing functions for easyness
Spacer.prototype.drawOutline = OutlinePainter('rgba(255, 0, 255, 0.5)');

Graph.Claim.prototype.drawOutline = OutlinePainter('rgba(255, 255, 0, 0.5)');

});

if (typeof module !== 'undefined')
	module.exports = patch;
else
	patch(window.Graph);

})();