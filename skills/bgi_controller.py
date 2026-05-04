import os
import json
import subprocess
import config
from api import feishu_api


def execute_bgi_task(bgi_cmd, decision_lower, store, open_id, uid):
    """异步执行 BGI 逻辑（从原 feishu_main.py 拷贝，路径改为 config 常量）。"""
    try:
        bgi_cmd = bgi_cmd or {}
        energy_task = bgi_cmd.get("energy_task", {})
        free_tasks = bgi_cmd.get("free_task", [])

        target_domain = energy_task.get("target", "无")
        gather_items = [t.get("target") for t in free_tasks if t.get("action") == "gather"]
        gather_str = "、".join(gather_items) if gather_items else "无"

        config_path = config.BGI_ONE_DRAGON_CONFIG
        map_config_path = config.BGI_MAP_CONFIG

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                bgi_config = json.load(f)

            if energy_task.get("action") == "run_domain":
                bgi_config["DomainName"] = target_domain
                bgi_config["TaskEnabledList"]["自动秘境"] = True
                bgi_config["TaskEnabledList"]["自动地脉花"] = False
                bgi_config["TaskEnabledList"]["突破材料"] = False

            elif energy_task.get("action") == "run_leyline":
                bgi_config["TaskEnabledList"]["自动秘境"] = False
                bgi_config["TaskEnabledList"]["自动地脉花"] = True
                bgi_config["TaskEnabledList"]["突破材料"] = False
                bgi_config["LeyLineOneDragonMode"] = True

                global_config_path = config.BGI_GLOBAL_CONFIG
                if os.path.exists(global_config_path):
                    with open(global_config_path, "r", encoding="utf-8") as f:
                        global_config = json.load(f)

                    if "autoLeyLineOutcropConfig" not in global_config:
                        global_config["autoLeyLineOutcropConfig"] = {}

                    global_config["autoLeyLineOutcropConfig"]["leyLineOutcropType"] = target_domain

                    with open(global_config_path, "w", encoding="utf-8") as f:
                        json.dump(global_config, f, ensure_ascii=False, indent=4)
                    print(f"🌍 全局配置已更新：今日地脉目标锁定为【{target_domain}】")
                else:
                    print(f"⚠️ 找不到全局配置文件 {global_config_path}，无法设置地脉种类！")

            elif energy_task.get("action") == "run_boss":
                bgi_config["TaskEnabledList"]["自动秘境"] = False
                bgi_config["TaskEnabledList"]["自动地脉花"] = False
                bgi_config["TaskEnabledList"]["突破材料"] = True

                boss_config_path = config.BGI_BOSS_CONFIG

                boss_data = [{
                    "name": target_domain,
                    "totalCount": 100,
                    "remainingCount": 100,
                    "team": "挂机刷本专属",
                    "returnToStatueAfterEachRound": True,
                    "farmMode": "一次性",
                    "lastFarmTime": None,
                    "dailyLimitCount": 100,
                    "dailyRemainingCount": 100,
                    "fightParam": {"timeout": 240, "strategyName": "挂机刷本"},
                }]

                os.makedirs(os.path.dirname(boss_config_path), exist_ok=True)
                with open(boss_config_path, "w", encoding="utf-8") as f:
                    json.dump(boss_data, f, ensure_ascii=False, indent=4)
                print(f"👹 Boss 模块接管：已生成 {target_domain} 的高并发讨伐配置。")

            # 覆写地图素材
            if gather_items and os.path.exists(map_config_path):
                bgi_config["TaskEnabledList"]["地图素材"] = True
                with open(map_config_path, "r", encoding="utf-8") as f:
                    map_data = json.load(f)

                enabled_count = 0
                consecutive_disabled = 0
                for proj in map_data.get("projects", []):
                    folder_name = proj.get("folderName", "")
                    if any(item in folder_name for item in gather_items):
                        proj["status"] = "Enabled"
                        enabled_count += 1
                        consecutive_disabled = 0
                    else:
                        if consecutive_disabled >= 150:
                            proj["status"] = "Enabled"
                            enabled_count += 1
                            consecutive_disabled = 0
                            print(f"🛡️ [防闪退机制触发] 强制开启隔离路径: {proj.get('name')}")
                        else:
                            proj["status"] = "Disabled"
                            consecutive_disabled += 1

                with open(map_config_path, "w", encoding="utf-8") as f:
                    json.dump(map_data, f, ensure_ascii=False, indent=4)

                print(f"🗺️ 地图素材路线已重置，共激活 {enabled_count} 条跑图路线 (含防闪退隔离带)。")
            else:
                bgi_config["TaskEnabledList"]["地图素材"] = False

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(bgi_config, f, ensure_ascii=False, indent=4)

            print(f"\n📝 BetterGI 配置已动态覆写！今日死磕：{target_domain}，顺路采集：{gather_str}")

            # 发工资逻辑
            wallet = store.get("wallet", {"mora": 0, "exp_books": 0, "boss_mats": {}})
            if energy_task.get("action") == "run_leyline":
                if target_domain == "藏金之花":
                    wallet["mora"] += 480000
                    print(f"💰 记账成功：虚拟钱包入账 480,000 摩拉！当前存款：{wallet['mora']}")
                else:
                    wallet["exp_books"] += 40
                    print(f"📕 记账成功：虚拟钱包入账 40 本经验书！当前存款：{wallet['exp_books']}")
            elif energy_task.get("action") == "run_boss":
                boss_name = target_domain
                wallet["boss_mats"][boss_name] = wallet["boss_mats"].get(boss_name, 0) + 12
                print(f"👹 记账成功：虚拟仓库入账 12 个 {boss_name} 掉落材料！当前已积攒：{wallet['boss_mats'][boss_name]} 个")

            store["wallet"] = wallet
            # Persist store is responsibility of caller if needed

            # 启动或测试
            if decision_lower == 'y':
                print("🚀 正在通过任务计划启动 BetterGI 一条龙...")
                feishu_api.send_feishu_msg(open_id, "🚀 正在通过任务计划启动 BetterGI 一条龙...")
                cmd_primary = ["schtasks.exe", "/run", "/tn", r"\StartBetterGI"]
                cmd_fallback = ["schtasks.exe", "/run", "/tn", "StartBetterGI"]
                try:
                    result = subprocess.run(cmd_primary, capture_output=True)
                    if result.returncode != 0:
                        result = subprocess.run(cmd_fallback, capture_output=True)

                    if result.returncode == 0:
                        print("🎉 任务计划已触发，BetterGI 正在执行一条龙。")
                        feishu_api.send_feishu_msg(open_id, "🎉 任务计划已触发，BetterGI 正在执行一条龙。")
                    else:
                        def _decode(raw: bytes) -> str:
                            if not raw:
                                return ""
                            for enc in ("utf-8", "gbk", "cp936"):
                                try:
                                    return raw.decode(enc)
                                except UnicodeDecodeError:
                                    continue
                            return raw.decode("utf-8", errors="replace")

                        err = (_decode(result.stderr) or _decode(result.stdout) or "未知错误").strip()
                        print(f"❌ 任务计划启动失败: {err}")
                        feishu_api.send_feishu_msg(open_id, f"❌ 任务计划启动失败: {err}")
                except Exception as e:
                    print(f"❌ 启动 BetterGI 失败: {e}")
                    feishu_api.send_feishu_msg(open_id, f"❌ 启动 BetterGI 失败: {e}")
            else:
                print("🛠️ [测试模式] 配置文件覆写与虚拟账本更新已完成！成功跳过游戏启动环节。")
                feishu_api.send_feishu_msg(open_id, "🛠️ [测试模式] 配置文件覆写与虚拟账本更新已完成！成功跳过游戏启动环节。")

        else:
            print(f"❌ 找不到配置文件: {config_path}，请检查路径。跳过执行。")
            feishu_api.send_feishu_msg(open_id, f"❌ 找不到配置文件: {config_path}，请检查路径。跳过执行。")

    except Exception as e:
        print(f"❌ 发生错误: {e}")
        feishu_api.send_feishu_msg(open_id, f"❌ 执行配置时发生错误: {str(e)}")
