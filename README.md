# xml-tree
A tree viewer for XML documents

## Features
- [x] View XML files as a tree
- [x] Lazy load tree : https://www.qtcentre.org/threads/28082-QTreeView-own-model-dynamic-filling
- [ ] Free-text search across file (Find in xml then create ancestry and programatically expand ancestry)
- [ ] Show lists as Table
- [ ] Generate XPath for selected node
- [x] Support for HTML files
- [x] Syntax Highlighting
- [ ] Syntax Highlighting color theme
- [ ] Highlight all Matches
- [ ] ~~Exclude Matches~~  
- [x] Menu Recent Document lookup
- [x] Menu Collapse
- [x] Menu Expand
- [ ] ~~Menu Expand Selected~~
- [x] Menu Toggle Attributes
- [x] Menu Option Font
- [x] Context Menu Expand
- [x] Context Menu Collapse
- [ ] ~~Context Menu Expand All children~~
- [ ] Context Menu Remove Node
- [x] Context Menu Reload Tree
- [ ] ~~Context Menu Expand All~~
- [ ] ~~Context Menu Expand Selected~~
- [ ] Show Namespace  
- [ ] Find by XPath (Create a map of node to tree view item. Find Node, lookup item)
- [ ] Convert to JSON
- [x] Read JSON file
- [ ] Support showing of comments
- [ ] ~~Text based XML editor~~

## Bugs
- [ ] Long lines of text are not elided : https://stackoverflow.com/questions/66412941/qt-elide-rich-text
- [x] Color theme changes do not reflect on the menu until restart (Fixed: 2020.07.10)
- [x] Fonts are not saved in settings (Fixed: 2020.06.03)