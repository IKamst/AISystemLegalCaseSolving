jQuery(function($) {
    "use strict"

    class FavoriteStorage {
        constructor(key) {
            this.key = key;
            this.listeners = {};
        }

        get values() {
            try {
                return JSON.parse(window.localStorage[this.key]);
            } catch (e) {
                return [];
            }
        }

        set values(list) {
            window.localStorage[this.key] = JSON.stringify(list);
        }

        compare(a, b) {
            return a.sentence == b.sentence && a.grammar == b.grammar;
        }

        add(favorite) {
            this.values = this.values.concat([favorite]);
            this.dispatchEvent(['add', 'update'], {action: 'add', favorite: favorite});
        }

        remove(favorite) {
            this.values = this.values.filter(function(stored) {
                return !this.compare(stored, favorite);
            }, this);
            this.dispatchEvent(['remove', 'update'], {action: 'remove', favorite: favorite});
        }

        toggle(favorite) {
            if (this.contains(favorite))
                this.remove(favorite);
            else
                this.add(favorite);
        }

        contains(favorite) {
            return this.values.find(function(stored) {
                return this.compare(stored, favorite);
            }, this) !== undefined;
        }

        on(event, callback) {
            if (!(event in this.listeners))
                this.listeners[event] = [];

            this.listeners[event].push(callback);

            return callback;
        }

        dispatchEvent(event, data) {
            if (Array.isArray(event))
                return event.forEach(function(event) {
                    this.dispatchEvent(event, data);
                }, this);

            if (!(event in this.listeners))
                return;

            this.listeners[event].forEach(function(listener) {
                listener(data);
            });
        }
    }

    const favorites = new FavoriteStorage('favorites');

    const grammars = $('#parse-sentence-form .grammar-dropdown input[name=grammar]').map(function() {
        return {
            name: $(this).val(),
            label: $.trim($(this).parent().text())
        };
    });

    function notify(message) {
        let toastList = $('#toast-list');

        if (!toastList.length)
            toastList = $('<div id="toast-list">').appendTo(document.body);

        const toast = $('<div>')
            .addClass('alert alert-info toast')
            .append($('<p>').text(message))
            .prependTo(toastList);

        setTimeout(function() {
            toast.slideUp(400, function() {
                toast.remove();
            });
        }, 3e3);

        return toast;
    }

    function closeButton() {
        return $('<button type="button" class="close" aria-label="Close results" title="Close results"><span>&times;</span></button>');
    }

    function editButton(sentence, grammar) {
        return $('<button type="button" class="btn btn-hidden btn-xs edit-sentence" aria-label="Edit sentence" title="Edit sentence"><span class="glyphicon glyphicon-pencil" aria-hidden="true"></span></button>').data({'sentence': sentence, 'grammar': grammar});
    }

    function starButton(sentence, grammar) {
        const button = $('<button type="button" class="btn btn-hidden btn-xs star-sentence" aria-label="Remember sentence" title="Remember sentence"><span class="glyphicon" aria-hidden="true"></span></button>').data({'sentence': sentence, 'grammar': grammar});
        favorites.on('update', function() {
            const isFavorite = favorites.contains({sentence: sentence, grammar: grammar});
            button.find('.glyphicon')
                .removeClass('glyphicon-star glyphicon-star-empty')
                .addClass(isFavorite ? 'glyphicon-star' : 'glyphicon-star-empty');
        })();
        return button;
    }

    function repeatButton(sentence, grammar) {
        return $('<div class="btn-group repeat-sentence">')
            .data('sentence', sentence)
            .append(
                $('<button type="button" class="btn btn-xs btn-hidden repeat-sentence-action" aria-label="Parse again" title="Parse again"><span class="glyphicon glyphicon-repeat" aria-hidden="true"></span></button>'),
                $('<button type="button" class="btn btn-xs btn-hidden dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"><span class="caret"></span><span class="sr-only">Toggle Dropdown</span></button>'),
                $('<ul class="dropdown-menu dropdown-menu-right">')
                    .append(grammars.map(function() {
                        return $('<li>')
                            .append($('<label>')
                                .append($('<input type="radio" name="grammar">')
                                    .val(this.name)
                                    .prop({'checked': this.name == grammar}))
                                .append(document.createTextNode(' ' + this.label)));
                    }).toArray())
            );
    }

    $.fn.alert = function(message) {
        var $alert = $('<div>')
            .addClass('alert alert-danger alert-dismissible dismissible')
            .append($('<p>').css({'white-space': 'pre', 'overflow': 'auto'}).text(message));
        return $(this).prepend($alert);
    };

    $.fn.scrollIntoView = function() {
        var offsetTop = parseInt($('body').css('padding-top'));
        var position = $(this).position();
        var scrollTop = $('body').scrollTop();
        var winHeight = $('body').height();

        if (position.top - offsetTop < scrollTop
            || position.top - offsetTop > scrollTop + winHeight)
            $('body').scrollTop(position.top - offsetTop);

        return $(this);
    };

    function stringifyTokens(tokens) {
        return $('<div>').addClass('tokenized').append($.map(tokens, function(token, i) {
            return $('<span>')
                .addClass('token')
                .attr('data-pos', i + 1)
                .text(token.text)
                .prop('title', token.tag);
        }));
    }

    function stringifyParse(parse) {
        return stringifyStatement(parse);
    }

    function isType(type) {
        return function(arg) {
            return arg.type == type;
        };
    }

    function stringifyStatement(parse) {
        return $('<li>')
            .addClass('predicate')
            .append($('<strong>').text(parse.repr).attr('title', parse.repr))
            .append($('<ul>').addClass('source').append($.map(parse.sources || [], stringifyStatement)))
            .append($('<ul>').addClass('supports').append($.map(parse.args.filter(isType('support')), stringifyStatement)))
            .append($('<ul>').addClass('attacks').append($.map(parse.args.filter(isType('attack')), stringifyStatement)));
    }

    var globalIDCounter = 0;

    function treeElement(tree) {
        const label = typeof tree.label === 'string'
            ? $('<span>').text(tree.label).prop('title', tree.tooltip)
            : $('<span>').text(tree.label.text).prop('title', tree.label.tag);
        const leaf = $('<li>').append(label).data('state', tree.data);

        if ('nodes' in tree)
            leaf.append($('<ul>').append(tree.nodes.map(treeElement)));
        else
            label.addClass('literal');
        
        return leaf;
    }

    String.prototype.indent = function(prefix) {
        return this.split('\n').map((line) => prefix + line).join('\n');
    };

    String.prototype.capitalize = function() {
        return this.substring(0, 1).toUpperCase() + this.substring(1).toLowerCase();
    };

    function treeTikz(tree) {
        if (tree.nodes) {
            const leavestr = tree.nodes.some(node => tree.nodes)
                ? '\n' + tree.nodes.map(treeTikz).join('\n').indent('\t')
                : ' ' + tree.nodes.map(node => node.label).join(' ');
            return '[.' + treeTikzLabel(tree.label) + leavestr + ' ]';
        }
        else
            return '[.' + tree.label + ' ]';
    }

    function treeTikzLabel(label) {
        return label.toLowerCase().replace(/_/g, '-');
    }

    function graphifyParse(state, $canvas) {
        var graph = new Graph($canvas.get(0));

        var claims = {}, relations = {};

        state.claims.forEach(function(claim) {
            claims[claim.id] = graph.addClaim(claim.text, {assumption: claim.assumption, scope: claim.scope, tooltip: claim.tooltip});
        });

        // Make sure we first do all relations targeting claims, and only then
        // the ones targeting relations, so that the targets of the last group
        // already exists.
        state.relations
            .sort(function(a, b) {
                var as = a.target.cls == 'claim' ? 0 : 1;
                var bs = b.target.cls == 'claim' ? 0 : 1;
                return as - bs;
            })
            .forEach(function(relation) {
                var sources = relation.sources.sort((a, b) => a.id - b.id).map(function(source) {
                    switch (source.cls) {
                        case 'claim':
                            return claims[source.id];
                        default:
                            throw new Error("Unknown type '" + source.cls + "'");
                    }
                });

                var target;

                switch (relation.target.cls) {
                    case 'claim':
                        if (!(relation.target.id in claims))
                            throw new Error("Could not find target claim '" + relation.target.id + "'")
                        target = claims[relation.target.id];
                        break;
                    case 'relation':
                        if (!(relation.target.id in relations))
                            throw new Error("Could not find target relation '" + relation.target.id + "'")
                        target = relations[relation.target.id];
                        break;
                    default:
                        throw new Error("Unknown type '" + relation.target.cls + "'");
                }

                console.assert(!(relation.id in relations), 'relation id occurs multiple times');

                relations[relation.id] = graph.addRelation(sources, target, relation.type, {assumption: relation.assumption});
            });

        graph.layout().apply();

        graph.fitVertically(10);

        graph.on('drop', function() {
            graph.fitVertically(10);
        });

        return graph;
    }

    function networkifyParse(parse, i) {
        const $canvas = $('<canvas>').prop('tabIndex', 1);
        
        const graph = graphifyParse(parse.data, $canvas);

        const panel = $('<div>');

        const parseNumber = $('<span>').addClass('parse-number').text(i + 1).appendTo(panel);

        const toolbar = $('<div class="btn-toolbar" role="toolbar">').appendTo(panel);

        const viewButtons = $('<div class="btn-group btn-group-xs" role="group" aria-label="views">').appendTo(toolbar);

        const actionButtons = $('<div class="btn-group btn-group-xs" role="group" aria-label="actions">').appendTo(toolbar);

        const copyButton = $('<button class="btn btn-default copy-btn graph-copy-button"></button>')
            .prop('title', 'Copy graph to clipboard')
            .append('<span class="glyphicon glyphicon-copy"></span> Diagram')
            .appendTo(actionButtons)
            .click(function() {
                $(this).attr('data-clipboard-text', graph.toString());
                notify('HASL diagram copied to clipboard');
            });

        const treeCopyButton = $('<button class="btn btn-default copy-btn tree-copy-button"></button>')
            .prop('title', 'Copy parse tree to clipboard')
            .append('<span class="glyphicon glyphicon-copy"></span> Tree')
            .appendTo(actionButtons)
            .click(function() {
                $(this).attr('data-clipboard-text', treeTikz(parse.tree));
                notify('Tikz tree copied to clipboard');
            });

        function view(label, type, icon, constructor) {
            const container = $('<div>')
                .appendTo(panel)
                .addClass('collapse ' + type);
            
            const button = $('<button>')
                .appendTo(viewButtons)
                .addClass('btn btn-default')
                .prop('title', 'Toggle ' + label)
                .append($('<span>').addClass('glyphicon ' + icon))
                .append(document.createTextNode(' ' + label.capitalize()))
                .click(function() {
                    container.collapse('toggle');
                });

            container.on('show.bs.collapse', function() {
                button.addClass('active').attr('aria-pressed', 'true');
            });

            container.on('hide.bs.collapse', function() {
                button.removeClass('active').attr('aria-pressed', 'false');
            });

            constructor.call(container, button);
        }

        view('argument diagram', 'network', 'glyphicon-comment', function(button) {
            this.append($canvas);

            graph.on('mouseover', function(e) {
                $canvas.prop('title', e.target.data.tooltip);
            });

            graph.on('mouseout', function(e) {
                $canvas.prop('title', '');
            });

            // Show first 10 parses by default
            if (i < 10) this.collapse('show');
        });

        view('parse tree', 'tree', 'glyphicon-object-align-vertical', function() {
            this.append($('<ul>').append(treeElement(parse.tree)));
        });

        view('parse log', 'trace', 'glyphicon-sort-by-attributes', function() {
            this.append($('<ol>')
                .append($.map(parse.trace, function(step) {
                    return $('<li>').text(step);
                })));
        });

        view('list of entities', 'entities', 'glyphicon-tags', function() {
            this.append($('<pre>').text(JSON.stringify(parse.data.entities, null, '\t')));
        });

        return panel;
    }

    function listEntities(parse) {
        return $('<ul>').addClass('entity-list').append(parse.entities.map(function(entity) {
            return  $(document.createDocumentFragment())
                .append($('<li>').text(entity.repr))
                .append($('<ul>').append(entity.occurrences.map(function(occurrence) {
                    return $('<li>').text(occurrence.repr)
                })));
        }));
    }

    function parseSentence(sentence, grammar, location) {
        var panel = $('<div>')
            .addClass('parse panel panel-default dismissible')
            .append($('<div class="panel-heading">')
                .append(closeButton())
                .append(editButton(sentence, grammar || null))
                .append(repeatButton(sentence, grammar || null))
                .append(starButton(sentence, grammar || null))
                .on('dblclick', function(e) {
                    e.preventDefault();
                    $(this).parent().find('.panel-collapse').collapse('toggle');
                }));

        if (location) {
            location.replaceWith(panel);
        } else {
            $('#parses').prepend(panel);
        }

        const body = $('<div class="panel-collapse collapse in">').appendTo(panel);

        body.append('<span class="loading">Loading…</span>');

        $.get($('#parse-sentence-form').attr('action'), {sentence: sentence, grammar: grammar}, 'json')
            .always(function(response, status) {
                // No consistency :(
                if (status == 'error')
                    response = response.responseJSON || {};

                panel.find('.panel-heading').append(stringifyTokens(response.tokens || []));

                body.empty();

                if (response.warning)
                    alert(response.warning);

                switch (status) {
                    case 'success':
                        body.append($('<div class="panel-body list-group">')
                            .append($.map(response.parses, function(parse, i) {
                                return panel = $('<div>')
                                    .addClass('list-group-item')
                                    .append(networkifyParse(parse, i));
                            }))
                        );
                        break;

                    default:
                        try {
                            body.append($('<div class="panel-body">').alert(response.error));
                            var match = response.error.match(/\(at position (\d+)\)/);
                            if (match)
                                panel.find('[data-pos=' + match[1] + '].token').addClass('bg-danger');
                        } catch (e) {
                           body.append($('<div class="panel-body">').alert("Something went wrong on the server."));
                        }
                        break;
                }

                panel.scrollIntoView();
            });
    }

    function setDefaultGrammar(name) {
        const grammar = grammars.get().find((grammar) => grammar.name == name);
        if (grammar === undefined) throw Error('Unknown grammar: ' + name);
        $("#parse-sentence-form input[name=grammar][value='" + name + "']").prop('checked', true);
        $('#parse-sentence-form .current-grammar').text(grammar.label);
    }

    function addToHistory(sentence) {
        var history = JSON.parse(window.localStorage.history || '[]');
        history = history.filter((s) => s != sentence); // prevents double entries
        history.splice(9); // make sure the history is not too long
        history.unshift(sentence); // add the new sentence to the top
        window.localStorage.history = JSON.stringify(history);
    }

    function updateHistory() {
        var history = JSON.parse(window.localStorage.history || '[]');
        var dropdown = $('.history-dropdown').empty();
        dropdown.append(history.map(function(sentence) {
            return $('<li>').append(
                $('<a>')
                    .addClass('example-sentence')
                    .attr('href', '#')
                    .attr('title', sentence)
                    .text(sentence)
            );
        }));
    }

    $('body').on('click', '.tree li > span', function(e) {
        const state = $(this).closest('li').data('state');

        const $modal = $('\
            <div class="modal fade" tabindex="-1" role="dialog">\
              <div class="modal-dialog" role="document">\
                <div class="modal-content">\
                  <div class="modal-header">\
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>\
                  </div>\
                  <div class="modal-body">\
                    <ul class="nav nav-tabs">\
                      <li class="active"><a href="#modal-info-json" data-toggle="tab">Raw</a></li>\
                    </ul>\
                    <div class="tab-content">\
                      <div class="tab-pane active" id="modal-info-json"></div>\
                  </div>\
                </div>\
              </div>\
            </div>');

        $('<h4 class="modal-title">')
            .text($(this).text())
            .appendTo($modal.find('.modal-header'));
        
        $('<pre>')
            .text(JSON.stringify(state, null, 2))
            .appendTo($modal.find('#modal-info-json'));

        if (state.claims.length > 0) {
            const tab = $('<li><a href="#modal-info-graph" data-toggle="tab">Diagram</a></li>').appendTo($modal.find('.nav-tabs'));
            const content = $('<div class="tab-pane" id="modal-info-graph"><canvas></canvas></div>').appendTo($modal.find('.tab-content'));
            graphifyParse(state, content.find('canvas'));

            $modal.on('shown.bs.modal', function() {
                tab.find('a').tab('show');
            });
        }

        $modal.on('hidden.bs.modal', function() {
            $modal.remove();
        });

        $modal.modal('show');
    });

    $('body').on('click', '.history-toggle', updateHistory);

    $('#parse-sentence-form').on('change', 'input[name=grammar]', function(e) {
        window.localStorage.defaultGrammar = $(this).val();
        setDefaultGrammar($(this).val());
    });

    setDefaultGrammar(grammars[grammars.length - 1].name);
    try {
        if ('defaultGrammar' in window.localStorage)
            setDefaultGrammar(window.localStorage.defaultGrammar);
    } catch (e) {
        // No harm
    }
    
    $('body').on('click', '.dismissible button.close', function(e) {
        e.preventDefault();
        $(this).closest('.dismissible').remove();
    });

    $('body').on('click', '.edit-sentence', function(e) {
        setDefaultGrammar($(this).data('grammar'));
        $('#parse-sentence-form input[name=sentence]').val($(this).data('sentence')).get(0).focus();
    });

    $('body').on('click', '.repeat-sentence .repeat-sentence-action', function(e) {
        var sentence = $(this).closest('.repeat-sentence').data('sentence');
        var grammar = $(this).closest('.repeat-sentence').find('input[name=grammar]:checked').val();
        parseSentence(sentence, grammar, $(this).closest('.parse.panel'));
    });

    $('body').on('change', '.repeat-sentence input[name=grammar]', function(e) {
        parseSentence($(this).closest('.repeat-sentence').data('sentence'), $(this).val(), $(this).closest('.parse.panel'));
    });

    $('body').on('click', '.star-sentence', function(e) {
        favorites.toggle({sentence: $(this).data('sentence'), grammar: $(this).data('grammar')});
    });

    $('#parse-sentence-form').submit(function(e) {
        e.preventDefault();
        var sentence = $(this).find('input[name=sentence]').val();
        var grammar = $(this).find('input[name=grammar]:checked').val();
        addToHistory(sentence);
        parseSentence(sentence, grammar);
    });

    $('body').on('click', '.example-sentence', function(e) {
        e.preventDefault();
        var sentence = $(e.target).text();
        var grammar = $('#parse-sentence-form input[name=grammar]:checked').val();
        $('#parse-sentence-form input[name=sentence]').val(sentence);
        parseSentence(sentence, grammar);
    });

    $('body').on('click', '.test-all-sentences', function(e) {
        var list = $(this).parent().next('ul');
        var sentences = list.find('.example-sentence');
        var grammar = $('#parse-sentence-form input[name=grammar]:checked').val();
        
        sentences.each(function() {
            $(this).removeClass('test-valid test-ambiguous test-error');
        });

        sentences.each(function() {
            var li = $(this);
            var sentence = $(this).text();
            $.get($('#parse-sentence-form').attr('action'), {sentence: sentence, grammar: grammar}, 'json')
                .always(function(response, status) {
                    // No consistency :(
                    if (status == 'error' || response.parses.length == 0)
                        li.addClass('test-error');
                    else if (response.parses.length == 1)
                        li.addClass('test-valid');
                    else if (response.parses.length > 1)
                        li.addClass('test-ambiguous');
                });
        });
    });

    if ('Clipboard' in window)
        new Clipboard('.copy-btn');

    favorites.values.forEach(favorite => {
        parseSentence(favorite.sentence, favorite.grammar);
    });

    // var stream = new EventSource('/api/stream');
    // stream.onmessage = function(e) {
    //     console.info('Python:', e.data);
    // };
});