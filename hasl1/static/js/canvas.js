(function() {

var patch = (function(CanvasRenderingContext2D) {
/**
 * Draws a path (you have to call stroke or fill) of an arrow pointed in the
 * correct direction with lines of radius r.
 */
CanvasRenderingContext2D.prototype.arrow = function(r, fromx, fromy, tox, toy)
{
	this.beginPath();
	
	var angle = Math.atan2(toy - fromy, tox - fromx);

	// Move backwards to make room for the whole arrow
	tox -= r * Math.cos(angle);
	toy -= r * Math.sin(angle);
	
	// top
	this.moveTo(
		r * Math.cos(angle) + tox,
		r * Math.sin(angle) + toy);
	
	angle += (1 / 3) * 2 * Math.PI;
	
	// right
	this.lineTo(
		r * Math.cos(angle) + tox,
		r * Math.sin(angle) + toy);
	
	angle += (1 / 3) * 2 * Math.PI;
	
	// left
	this.lineTo(
		r * Math.cos(angle) + tox,
		r * Math.sin(angle) + toy);
	
	this.closePath();
};

CanvasRenderingContext2D.prototype.cross = function(r, fromx, fromy, tox, toy)
{
	this.beginPath();

	var angle = Math.atan2(toy - fromy, tox - fromx);

	var a = {
		x: r * Math.cos(angle + 0.5 * Math.PI) + tox,
		y: r * Math.sin(angle + 0.5 * Math.PI) + toy
	};

	var b = {
		x: r * Math.cos(angle - 0.5 * Math.PI) + tox,
		y: r * Math.sin(angle - 0.5 * Math.PI) + toy
	};

	this.moveTo(a.x - 0.5 * r * Math.cos(angle), a.y - 0.5 * r * Math.sin(angle));

	this.lineTo(b.x - 2.5 * r * Math.cos(angle), b.y - 2.5 * r * Math.sin(angle));

	this.moveTo(b.x - 0.5 * r * Math.cos(angle), b.y - 0.5 * r * Math.sin(angle));

	this.lineTo(a.x - 2.5 * r * Math.cos(angle), a.y - 2.5 * r * Math.sin(angle));
};

CanvasRenderingContext2D.prototype.wrapText = function(text, maxWidth)
{
	// Todo: use https://github.com/bramstein/hypher/blob/master/lib/hypher.js for hypens
	const words = text.split(/\s+/);

	const lines = [];
	let line = [];

	for (let i = 0; i < words.length; ++i) {
		line.push(words[i]);

		if (this.measureText(line.join(' ')).width > maxWidth) {
			line.pop();
			lines.push(line.join(' '));
			line = [words[i]];
		}
	}

	if (line.length)
		lines.push(line.join(' '));

	return lines;
};

});

if (typeof module !== 'undefined')
	module.exports = patch;
else
	patch(window.CanvasRenderingContext2D);

})();