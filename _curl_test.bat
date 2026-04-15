@echo off
chcp 65001 >nul
curl -s -X POST http://127.0.0.1:5001/generate-worldview -H "Content-Type: application/json" -d "{\"gameTheme\":\"便利店深夜\",\"protagonistAttr\":{\"looks\":\"普通\",\"intelligence\":\"普通\",\"stamina\":\"普通\",\"charisma\":\"普通\"},\"difficulty\":\"中等\",\"toneKey\":\"normal_ending\",\"imageStyle\":\"anime\"}" --max-time 60
echo.
echo Done
