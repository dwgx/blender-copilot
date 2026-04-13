# Mayo VRC Avatar - Complete Operation Manual
# Mayo VRC 模型完整操作手冊

> 本手冊記錄了 Mayo avatar 從 Blender 到 VRChat 的完整流水線，
> 包含遇到的所有問題、解決方案、以及給未來 Agent 的接手指南。

---

## 1. 項目概況

| 項目 | 詳情 |
|---|---|
| **模型** | Mayo (まよ) by Chocolate rice, BOOTH #8122803 |
| **Blender 文件** | `桌面/8122803-MAYO_ver.1.01_Chocolate_rice/MAYO_VRC_Enhanced.blend` |
| **導出 FBX** | `同目錄/MAYO_VRC_Export.fbx` (64MB, 47 meshes) |
| **知識庫** | `D:/WorkSpace/3DMCP/MODELER_KNOWLEDGE_BASE.md` |
| **MCP 工具** | `D:/WorkSpace/3DMCP/blender-mcp/` — 128+ 工具含 23 VRC 專用 |
| **動畫包** | 245+ 動畫 (EmoteBox x3 + EmoteSet Free + AnoWaza + DaoEmotes) |

### Blender 場景結構 (Collections)

```
Scene Collection
├── Mayo_Body          — 主體 mesh (Body, Body_2)
├── Mayo_Hair          — 原始髮型 (8 mesh parts)
├── Mayo_Clothing      — 原始衣服 (Dress, Arm_Belt, Leg_Belt, Kemomimi, Kemoshippo)
├── Mayo_Shoes_Original — 原始鞋子
├── Acc_BeachSandals   — 沙灘鞋 [新建] (BeachSandal_L, BeachSandal_R)
├── Acc_Soffina_Shoes  — Soffina 高跟鞋 [已修復]
├── Acc_MayoMayo       — 蛋黃醬瓶衣服 (MAYO.001, MAYO_Lid.001, Mayonnaise.001)
├── Acc_Condiment      — 調味品配件
├── Acc_TwinLady_Hair  — Twin Lady 髮型 (18 parts, 79 骨骼)
├── Acc_TwinLady_Accessories — Twin Lady 耳環/緞帶
└── Scene_Lights       — 場景燈光
```

### 主骨架: `Armature` (352 bones)
- 腳部骨骼: `Foot.L`, `Foot.R`, `Toe.L`, `Toe.R`
- 腿部: `Upper_leg.L/R`, `Lower_leg.L/R`

---

## 2. 遇到的問題及解決方案

### 問題 1: 鞋子歪了 (Soffina Shoes 軸向錯誤)

**症狀**: 鞋子在 Blender 中顯示為旋轉了 90 度

**根因**:
- FBX 導入時沒指定軸向參數
- 父級 Empty (`chr_shoes_b_universal`) 有 `rotation_euler.X = 90°` 和 `scale = 0.01`
- 這些 transform 沒有被 apply

**解決方案**:
```python
# 1. 解除父子關係，保留世界座標
shoes.parent = None  # 保持 matrix_world
# 2. 刪除中間的 Empty 層級
# 3. Apply transforms (Ctrl+A)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# 4. 重新 parent 到主骨架，按 X 座標分左右權重
```

**預防措施** (已加入工具):
- `vrc_import_model` 現在有 `fbx_preset` 參數 (default/unity/mixamo/mmd)
- `vrc_import_model` 現在有 `apply_transforms=True` 自動凍結
- `vrc_accessory_auto_align` 新工具 — 自動檢測並修正軸向/縮放

### 問題 2: 蛋黃醬瓶太大

**結論**: 不是 bug。`Mayo_Mayo` 就是梗衣服，設計就是一個巨大蛋黃醬瓶穿在身上。
- 組成: MAYO_Lid (瓶蓋 97 verts) + Mayonnaise (瓶身 248 verts) + MAYO (底座 541 verts)

### 問題 3: Expression Menu / 換裝不能用

**根因**: Expression Menu、Toggle、Radial Puppet 是 **Unity 側功能**，不是 Blender。
Blender 只負責 mesh 整理和骨骼綁定。

**正確做法**: 在 Unity 中用 VRCFury Toggle + Exclusive Tags

### 問題 4: UnityPackage 無法直接導入 Blender

**解決方案**: Python 腳本用 `tarfile` 解壓 `.unitypackage`，提取其中的 `.fbx` 文件
```python
import tarfile
with tarfile.open('xxx.unitypackage', 'r:gz') as tar:
    # 遍歷 pathname 文件找到 FBX 路徑
    # 用對應的 asset 文件提取
```

### 問題 5: Windows GBK 編碼錯誤

**症狀**: Python 輸出含 emoji 或日文時 `UnicodeEncodeError: 'gbk' codec`

**解決方案**: 在腳本開頭加
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

### 問題 6: Blender MCP Addon 不自動啟動

**症狀**: blender-mcp 工具無法連接，TCP port 9876 拒絕連線

**原因**: Blender 5.1 的 addon 需要手動啟用，或 autostart 腳本沒加載

**解決方案**:
1. 檢查 `C:\Users\dwgx1\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\startup\mcp_autostart.py`
2. 或手動: Blender > Edit > Preferences > Add-ons > 搜索 "MCP" > 啟用
3. 備用方案: 用 `blender_exec.py` 直連 socket (見下方)

### 問題 7: Unity 版本不對

**已安裝的錯誤版本**:
- Unity 2019.4.31f1 — 太舊 (已刪除)
- Unity 6000.4.2f1 — 太新 (Unity 6)

**VRChat 要求**: **Unity 2022.3.22f1** (截至 2026-04)

**最佳安裝方式**: 用 VRChat Creator Companion (VCC)，自動安裝正確版本

---

## 3. 工具鏈速查

### Blender 直連 Helper (當 MCP addon 無法連接時)

文件: `D:/WorkSpace/3DMCP/blender_exec.py`

```bash
# 用法 (Blender addon 必須在 port 9876 上運行)
python blender_exec.py "import bpy; print(bpy.context.scene.name)"
```

### MCP 工具鏈 (推薦順序)

```
vrc_import_model(fbx_preset="unity", apply_transforms=True)
  → vrc_accessory_auto_align(accessory_name="shoes", target_bone="Foot.L")
  → vrc_attach_accessory(auto_scale=True, rotation_correction="X90")
  → vrc_fix_model → vrc_rename_bones → vrc_setup_visemes
  → vrc_validate → vrc_export_fbx
```

### 關鍵常量位置

| 常量 | 文件 |
|---|---|
| VRC_FBX_EXPORT_SETTINGS | `vrc_constants.py` line 172 |
| VRC_FBX_IMPORT_PRESETS | `vrc_constants.py` line 187 (新增) |
| ACCESSORY_BONE_TARGETS | `vrc_constants.py` line 230 (新增) |
| BONE_NAME_MAP (100+ 映射) | `vrc_constants.py` |
| PHYSBONE_PRESETS (8 種) | `vrc_constants.py` |

---

## 4. Unity 端完整步驟 (給用戶)

### Step 0: 安裝正確的 Unity

1. 下載 VRChat Creator Companion: https://vrchat.com/home/download
2. 安裝 VCC → 它會自動安裝 Unity 2022.3.22f1
3. 或手動: Unity Hub → Installs → Archive → 搜索 2022.3.22f1

### Step 1: 創建 VRC 項目

1. VCC → New Project → Avatar → 命名 "Mayo_Avatar"
2. Manage Project → 添加:
   - VRCFury
   - Modular Avatar (MA)
   - anatawa12 AvatarOptimizer (可選)
3. Open Project

### Step 2: 導入資源

1. 拖 `MAYO_VRC_Export.fbx` 到 Assets
2. 選中 FBX → Inspector → Rig → **Humanoid** → Apply
3. 拖 FBX 到 Hierarchy (場景)
4. 匯入 EmoteBox `.unitypackage` (拖進 Unity)

### Step 3: 設定 Avatar Descriptor

1. 選中場景裡的 Mayo
2. Add Component → VRC Avatar Descriptor
3. View Position → Auto 或手動到兩眼之間
4. Viseme → Blend Shape → Face Mesh = Body

### Step 4: 設定衣服 Toggle (換裝)

每個要切換的部件 (沙灘鞋、Soffina 鞋、Mayo 瓶衣服、Twin Lady 髮型):
1. 選中物體 → Add Component → VRCFury → Toggle
2. 勾 Saved
3. 設 Exclusive Tag:
   - 鞋子都用 `shoes` → 穿沙灘鞋時自動脫 Soffina
   - 髮型用 `hair`
   - 衣服用 `outfit`

### Step 5: 匯入動畫

1. 拖 EmoteBox `.unitypackage` 進 Unity → Import
2. 找 MA Prefab (如 EmoteBox_32slot)
3. 拖到 Mayo 下作為子物體
4. 動畫自動出現在 Expression Menu

### Step 6: 上傳

1. VRChat SDK → Show Control Panel → 登入
2. Build & Publish
3. 填名字、描述 → Upload

---

## 5. 給未來 Agent 的接手指南

### 啟動清單

1. **讀取記憶**: `C:\Users\dwgx1\.claude\projects\D--WorkSpace-3DMCP\memory\MEMORY.md`
2. **讀取知識庫**: `D:/WorkSpace/3DMCP/MODELER_KNOWLEDGE_BASE.md`
3. **讀取本手冊**: `D:/WorkSpace/3DMCP/MAYO_VRC_MANUAL.md`
4. **確認 Blender addon**: 嘗試連接 `localhost:9876`，不通就用 `blender_exec.py`

### 常見任務

| 任務 | 工具 | 注意事項 |
|---|---|---|
| 導入配件 FBX | `vrc_import_model(fbx_preset="unity")` | 必須指定 preset |
| 對齊配件 | `vrc_accessory_auto_align` | 先 align 再 attach |
| 綁定到骨骼 | `vrc_attach_accessory(auto_scale=True)` | 鞋子綁 Foot.L/R |
| 導出 FBX | `vrc_export_fbx` 或手動 | -Z forward, Y up, 無 leaf bones |
| 驗證性能 | `vrc_validate` | PC Good = 70K tris, 8 mats |
| 修復模型 | `vrc_fix_model` | 只在有 armature 時執行 |

### 已知陷阱

1. **FBX 軸向**: BOOTH 素材多數從 Unity 導出，用 `fbx_preset="unity"`
2. **Apply Transforms**: 每次修改 scale/rotation 後必須 apply
3. **Expression Menu 不是 Blender 的事**: 永遠不要告訴用戶 Blender 端已經 "完成換裝"
4. **GBK 編碼**: Windows 環境 Python 必須 `sys.stdout.reconfigure(encoding='utf-8')`
5. **Blender 5.1 temp_override**: 無頭操作用 `bpy.context.temp_override(area=area)`
6. **多個 Blender 實例**: socket port 9876 只連到一個實例，注意不要混
7. **Mayo_Mayo 不是 bug**: 它就是一個巨型蛋黃醬瓶梗衣服

### 快捷流程 (30 秒版)

```
# 最快導入配件流程
vrc_import_model(filepath, fbx_preset="unity", apply_transforms=True)
vrc_accessory_auto_align(accessory_name, target_bone="Foot.L")
vrc_attach_accessory(accessory_name, target_bone="Foot.L", auto_scale=True)
# 驗證
vrc_validate()
# 導出
vrc_export_fbx()
```

---

## 6. 文件清單

```
桌面/8122803-MAYO_ver.1.01_Chocolate_rice/
├── MAYO_VRC_Enhanced.blend     — Blender 主文件 (含所有配件)
├── MAYO_VRC_Export.fbx         — Unity 用導出 (64MB)
├── MAYO_VRC_Project.blend      — 原始項目 (舊版)
├── FBX/                        — 原始 FBX 文件
├── Mayo_Free_Assets/           — 下載的免費素材
│   ├── _extracted/             — 從 UnityPackage 提取的 FBX
│   ├── ThreeLineSliper_Mayo_1.0/ — 拖鞋 (已刪除)
│   ├── Shoes_002_Universal/    — Soffina 鞋 (已修復)
│   ├── Mayo_Mayo/              — 蛋黃醬瓶衣服
│   ├── Mayo_May1/              — Twin Lady 套裝
│   ├── Mayo_Natural_make_up/   — 自然妝貼圖
│   ├── Mayo__makeup_texture/   — 化妝貼圖
│   └── yami_mayo/              — Yami 眼睛貼圖
└── Mayo 動畫包/
    ├── EmoteBox v3.3.unitypackage
    ├── EmoteBox+FX v1.0.unitypackage
    ├── EmoteBox Nccy v2.1.unitypackage
    ├── EmoteSet Free v1.3.unitypackage
    ├── AnoWaza Motion v3.0.unitypackage
    └── DaoEmotesBundle/
```

---

*Created: 2026-04-13 | By: Claude Opus 4.6 + dwgx*
*Last updated: 2026-04-13*
