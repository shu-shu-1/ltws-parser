import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import rtoml
from pathlib import Path
from typing import Dict, Any, Optional

from .models import WallpaperSource
from .parser import LTWSParser
from .validator import LTWSValidator
from .packager import LTWSPackager

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind('<Enter>', self._bound_to_mousewheel)
        self.canvas.bind('<Leave>', self._unbound_to_mousewheel)

    def _bound_to_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbound_to_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(self.tooltip, text=self.text, background="#ffffe0", relief="solid", borderwidth=1)
        label.pack()

    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

class EditorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LittleTree Wallpaper Source Editor")
        self.geometry("1200x800")
        
        # Set theme
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "clam" in style.theme_names():
            style.theme_use("clam")

        self.current_file_path: Optional[Path] = None
        self.source_data: Dict[str, Any] = self._create_empty_source()
        
        self._init_ui()
        self._create_menu()

    def _create_empty_source(self) -> Dict[str, Any]:
        return {
            "metadata": {
                "scheme": "littletree_wallpaper_source_v3",
                "identifier": "com.example.wallpaper",
                "name": "New Source",
                "version": "1.0.0",
                "logo": ""
            },
            "config": {},
            "categories": [],
            "apis": []
        }

    def _init_ui(self):
        # Main container
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left Sidebar (Navigation)
        self.nav_frame = ttk.Frame(self.paned_window, width=250)
        self.paned_window.add(self.nav_frame, weight=1)

        self.tree = ttk.Treeview(self.nav_frame, show="tree")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Right Content Area
        self.content_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.content_frame, weight=4)
        
        self._refresh_tree()

    def _create_menu(self):
        menubar = tk.Menu(self)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="新建 (New)", command=self.new_source)
        file_menu.add_command(label="打开 (Open Folder)", command=self.open_source)
        file_menu.add_command(label="保存 (Save)", command=self.save_source)
        file_menu.add_separator()
        file_menu.add_command(label="导出 .ltws (Export)", command=self.export_source)
        file_menu.add_separator()
        file_menu.add_command(label="退出 (Exit)", command=self.quit)
        menubar.add_cascade(label="文件 (File)", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="验证源 (Validate)", command=self.validate_source)
        menubar.add_cascade(label="工具 (Tools)", menu=tools_menu)

        self.config(menu=menubar)

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        
        # Root nodes
        self.tree.insert("", "end", "metadata", text="元数据 (Metadata)")
        self.tree.insert("", "end", "categories", text="分类 (Categories)")
        
        apis_node = self.tree.insert("", "end", "apis", text="APIs")
        for i, api in enumerate(self.source_data.get("apis", [])):
            self.tree.insert(apis_node, "end", f"api_{i}", text=api.get("name", f"API {i+1}"))

    def _on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        item_id = selected[0]
        self._clear_content()

        if item_id == "metadata":
            self._show_metadata_editor()
        elif item_id == "categories":
            self._show_categories_editor()
        elif item_id == "apis":
            self._show_apis_list()
        elif item_id.startswith("api_"):
            index = int(item_id.split("_")[1])
            self._show_api_editor(index)

    def _clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    # --- Editors ---

    def _show_metadata_editor(self):
        frame = ScrollableFrame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True)
        content = frame.scrollable_frame

        ttk.Label(content, text="元数据编辑", font=("", 16, "bold")).pack(pady=10, anchor="w")

        self._create_entry(content, "标识符 (Identifier):", self.source_data["metadata"], "identifier")
        self._create_entry(content, "名称 (Name):", self.source_data["metadata"], "name")
        self._create_entry(content, "版本 (Version):", self.source_data["metadata"], "version")
        self._create_entry(content, "协议 (Scheme):", self.source_data["metadata"], "scheme", readonly=True)
        self._create_entry(content, "Logo URL:", self.source_data["metadata"], "logo")

    def _show_categories_editor(self):
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(frame, text="分类管理", font=("", 16, "bold")).pack(pady=10, anchor="w")

        # Toolbar
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=5)
        ttk.Button(toolbar, text="添加分类", command=self._add_category).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="删除选中", command=lambda: self._delete_category(tree)).pack(side=tk.LEFT, padx=5)

        # Treeview for categories
        columns = ("id", "name", "category", "subcategory")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        tree.heading("id", text="ID")
        tree.heading("name", text="名称")
        tree.heading("category", text="一级分类")
        tree.heading("subcategory", text="二级分类")
        
        tree.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        # Populate
        for cat in self.source_data.get("categories", []):
            tree.insert("", "end", values=(cat.get("id"), cat.get("name"), cat.get("category"), cat.get("subcategory")))

        tree.bind("<Double-1>", lambda e: self._edit_category(tree))

    def _show_apis_list(self):
        frame = ttk.Frame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(frame, text="API 列表", font=("", 16, "bold")).pack(pady=10, anchor="w")

        ttk.Button(frame, text="添加 API", command=self._add_api).pack(pady=5, anchor="w")

        for i, api in enumerate(self.source_data.get("apis", [])):
            f = ttk.Frame(frame, relief="solid", borderwidth=1)
            f.pack(fill=tk.X, pady=5, padx=5)
            ttk.Label(f, text=api.get("name", "Unnamed API"), font=("", 12, "bold")).pack(side=tk.LEFT, padx=10, pady=10)
            ttk.Button(f, text="编辑", command=lambda idx=i: self._select_api(idx)).pack(side=tk.RIGHT, padx=5)
            ttk.Button(f, text="删除", command=lambda idx=i: self._delete_api(idx)).pack(side=tk.RIGHT, padx=5)

    def _select_api(self, index):
        # Select in tree to trigger editor
        self.tree.selection_set(f"api_{index}")
        self._show_api_editor(index)

    def _show_api_editor(self, index):
        api_data = self.source_data["apis"][index]
        
        frame = ScrollableFrame(self.content_frame)
        frame.pack(fill=tk.BOTH, expand=True)
        content = frame.scrollable_frame

        ttk.Label(content, text=f"编辑 API: {api_data.get('name')}", font=("", 16, "bold")).pack(pady=10, anchor="w")

        notebook = ttk.Notebook(content)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # General Tab
        tab_general = ttk.Frame(notebook)
        notebook.add(tab_general, text="基本信息")
        self._create_entry(tab_general, "名称 (Name):", api_data, "name")
        self._create_entry(tab_general, "描述 (Description):", api_data, "description")
        
        # Categories Selection
        ttk.Label(tab_general, text="关联分类 (Categories):").pack(anchor="w", padx=5, pady=5)
        cats_frame = ttk.Frame(tab_general)
        cats_frame.pack(fill=tk.X, padx=5)
        
        # Simple multi-select listbox for categories
        cat_listbox = tk.Listbox(cats_frame, selectmode=tk.MULTIPLE, height=5)
        cat_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        all_cats = [c.get("id") for c in self.source_data.get("categories", [])]
        current_cats = api_data.get("categories", [])
        
        for cat_id in all_cats:
            cat_listbox.insert(tk.END, cat_id)
            if cat_id in current_cats:
                cat_listbox.selection_set(tk.END)
        
        def update_cats(event):
            selected_indices = cat_listbox.curselection()
            api_data["categories"] = [cat_listbox.get(i) for i in selected_indices]
        
        cat_listbox.bind("<<ListboxSelect>>", update_cats)


        # Request Tab
        tab_request = ttk.Frame(notebook)
        notebook.add(tab_request, text="请求配置")
        if "request" not in api_data:
            api_data["request"] = {}
        req_data = api_data["request"]
        
        self._create_entry(tab_request, "URL:", req_data, "url")
        self._create_combobox(tab_request, "Method:", req_data, "method", ["GET", "POST"])
        self._create_entry(tab_request, "User Agent:", req_data, "user_agent")
        
        # Parameters Tab
        tab_params = ttk.Frame(notebook)
        notebook.add(tab_params, text="参数定义")
        self._create_params_editor(tab_params, api_data)

        # Mapping Tab
        tab_mapping = ttk.Frame(notebook)
        notebook.add(tab_mapping, text="字段映射")
        if "mapping" not in api_data:
            api_data["mapping"] = {}
        map_data = api_data["mapping"]
        
        ttk.Label(tab_mapping, text="单图模式字段:", font=("", 10, "bold")).pack(anchor="w", padx=5, pady=5)
        self._create_entry(tab_mapping, "图片URL (image):", map_data, "image")
        self._create_entry(tab_mapping, "缩略图 (thumbnail):", map_data, "thumbnail")
        self._create_entry(tab_mapping, "标题 (title):", map_data, "title")
        
        ttk.Label(tab_mapping, text="多图模式字段:", font=("", 10, "bold")).pack(anchor="w", padx=5, pady=10)
        self._create_entry(tab_mapping, "列表路径 (items):", map_data, "items")
        
        # Response Tab
        tab_response = ttk.Frame(notebook)
        notebook.add(tab_response, text="响应配置")
        if "response" not in api_data:
            api_data["response"] = {}
        # Simple JSON editor for response config could be added here

    def _create_params_editor(self, parent, api_data):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=5)
        
        # Define tree first
        cols = ("key", "type", "label", "default")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=5)
        for c in cols:
            tree.heading(c, text=c.capitalize())
            tree.column(c, width=100)
        tree.pack(fill=tk.BOTH, expand=True)

        def refresh_list():
            tree.delete(*tree.get_children())
            for p in api_data.get("parameters", []):
                tree.insert("", "end", values=(p.get("key"), p.get("type"), p.get("label"), p.get("default")))

        def add_param():
            new_param = {
                "key": "new_param",
                "type": "text",
                "label": "New Parameter"
            }
            if "parameters" not in api_data:
                api_data["parameters"] = []
            api_data["parameters"].append(new_param)
            refresh_list()

        def delete_param():
            selected = tree.selection()
            if not selected: return
            idx = tree.index(selected[0])
            del api_data["parameters"][idx]
            refresh_list()

        ttk.Button(toolbar, text="添加参数", command=add_param).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="删除参数", command=delete_param).pack(side=tk.LEFT, padx=5)

        refresh_list()
        
        tree.bind("<Double-1>", lambda e: self._edit_parameter(tree, api_data, refresh_list))

    def _edit_parameter(self, tree, api_data, callback):
        selected = tree.selection()
        if not selected:
            return
        idx = tree.index(selected[0])
        param = api_data["parameters"][idx]
        
        # Simple dialog to edit parameter
        dialog = tk.Toplevel(self)
        dialog.title("编辑参数")
        
        self._create_entry(dialog, "Key:", param, "key")
        self._create_combobox(dialog, "Type:", param, "type", ["text", "choice", "boolean"])
        self._create_entry(dialog, "Label:", param, "label")
        self._create_entry(dialog, "Default:", param, "default")
        
        def save():
            dialog.destroy()
            if callback:
                callback()
            
        ttk.Button(dialog, text="确定", command=save).pack(pady=10)


    # --- Helpers ---

    def _create_entry(self, parent, label_text, data_dict, key, readonly=False):
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(f, text=label_text, width=20).pack(side=tk.LEFT)
        var = tk.StringVar(value=data_dict.get(key, ""))
        
        def on_change(*args):
            data_dict[key] = var.get()
            
        var.trace_add("write", on_change)
        
        entry = ttk.Entry(f, textvariable=var)
        if readonly:
            entry.state(["readonly"])
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        return entry

    def _create_combobox(self, parent, label_text, data_dict, key, values):
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(f, text=label_text, width=20).pack(side=tk.LEFT)
        var = tk.StringVar(value=data_dict.get(key, ""))
        
        def on_change(*args):
            data_dict[key] = var.get()
        
        var.trace_add("write", on_change)
        
        cb = ttk.Combobox(f, textvariable=var, values=values)
        cb.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # --- Actions ---

    def new_source(self):
        if messagebox.askyesno("确认", "新建将丢失未保存的更改，是否继续？"):
            self.source_data = self._create_empty_source()
            self.current_file_path = None
            self._refresh_tree()

    def open_source(self):
        path = filedialog.askdirectory()
        if not path:
            return
        
        try:
            parser = LTWSParser(strict=False)
            source_obj = parser.parse(path)
            # Convert back to dict for editing
            self.source_data = source_obj.model_dump()
            self.current_file_path = Path(path)
            self._refresh_tree()
            messagebox.showinfo("成功", "加载成功")
        except Exception as e:
            messagebox.showerror("错误", f"加载失败: {str(e)}")

    def save_source(self):
        if not self.current_file_path:
            path = filedialog.askdirectory(title="选择保存目录")
            if not path:
                return
            self.current_file_path = Path(path)
        
        try:
            self._save_to_disk(self.current_file_path)
            messagebox.showinfo("成功", "保存成功")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")

    def _save_to_disk(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        
        # Split data into source.toml and categories.toml
        source_toml_data = {
            "metadata": self.source_data.get("metadata", {}),
            "config": self.source_data.get("config", {}),
            "apis": self.source_data.get("apis", [])
        }
        
        categories_toml_data = {
            "categories": self.source_data.get("categories", [])
        }
        
        with open(path / "source.toml", "w", encoding="utf-8") as f:
            rtoml.dump(source_toml_data, f)
            
        with open(path / "categories.toml", "w", encoding="utf-8") as f:
            rtoml.dump(categories_toml_data, f)

    def export_source(self):
        if not self.current_file_path:
            messagebox.showwarning("警告", "请先保存源文件")
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".ltws", filetypes=[("LTWS Package", "*.ltws")])
        if not file_path:
            return
            
        try:
            # Ensure current state is saved to disk first
            self._save_to_disk(self.current_file_path)
            
            packager = LTWSPackager(strict=False)
            packager.pack(str(self.current_file_path), file_path, overwrite=True)
            messagebox.showinfo("成功", f"导出成功: {file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def validate_source(self):
        try:
            # Create object from current data
            source_obj = WallpaperSource(**self.source_data)
            validator = LTWSValidator()
            is_valid = validator.validate_source(source_obj)
            
            msg = "验证通过！" if is_valid else "验证发现问题："
            if validator.errors:
                msg += "\n\n错误:\n" + "\n".join(validator.errors)
            if validator.warnings:
                msg += "\n\n警告:\n" + "\n".join(validator.warnings)
                
            if is_valid and not validator.warnings:
                messagebox.showinfo("验证结果", msg)
            else:
                messagebox.showwarning("验证结果", msg)
                
        except Exception as e:
            messagebox.showerror("验证错误", f"数据结构无效: {str(e)}")

    # --- Category Actions ---
    def _add_category(self):
        new_cat = {
            "id": "new_category",
            "name": "New Category",
            "category": "General"
        }
        self.source_data["categories"].append(new_cat)
        self._clear_content()
        self._show_categories_editor() # Refresh

    def _delete_category(self, tree):
        selected = tree.selection()
        if not selected:
            return
        idx = tree.index(selected[0])
        del self.source_data["categories"][idx]
        self._clear_content()
        self._show_categories_editor()

    def _edit_category(self, tree):
        selected = tree.selection()
        if not selected:
            return
        idx = tree.index(selected[0])
        cat = self.source_data["categories"][idx]
        
        dialog = tk.Toplevel(self)
        dialog.title("编辑分类")
        
        self._create_entry(dialog, "ID:", cat, "id")
        self._create_entry(dialog, "名称:", cat, "name")
        self._create_entry(dialog, "一级分类:", cat, "category")
        self._create_entry(dialog, "二级分类:", cat, "subcategory")
        
        def save():
            dialog.destroy()
            self._clear_content()
            self._show_categories_editor()

        ttk.Button(dialog, text="确定", command=save).pack(pady=10)

    # --- API Actions ---
    def _add_api(self):
        new_api = {
            "name": "New API",
            "categories": [],
            "request": {"url": "https://"},
            "mapping": {}
        }
        self.source_data["apis"].append(new_api)
        self._refresh_tree()
        self._clear_content()
        self._show_apis_list()

    def _delete_api(self, index):
        if messagebox.askyesno("确认", "确定删除此 API？"):
            del self.source_data["apis"][index]
            self._refresh_tree()
            self._clear_content()
            self._show_apis_list()

def main():
    app = EditorApp()
    app.mainloop()

if __name__ == "__main__":
    main()
