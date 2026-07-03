import { Link, Outlet } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "仪表盘" },
  { to: "/registration", label: "访客登记" },
  { to: "/summary", label: "汇总总表" },
  { to: "/live-board", label: "现场实时看板" },
  { to: "/cards", label: "写卡管理" },
  { to: "/templates", label: "欢迎词模板" },
  { to: "/work-logs", label: "工作日志" },
  { to: "/settings", label: "系统设置" },
];

export function NavLayout() {
  return (
    <div>
      <nav>
        <ul>
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <Link to={item.to}>{item.label}</Link>
            </li>
          ))}
        </ul>
      </nav>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
