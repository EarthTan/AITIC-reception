import { createBrowserRouter } from "react-router-dom";
import { NavLayout } from "./components/NavLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { RegistrationPage } from "./pages/RegistrationPage";
import { SummaryPage } from "./pages/SummaryPage";
import { LiveBoardPage } from "./pages/LiveBoardPage";
import { CardManagementPage } from "./pages/CardManagementPage";
import { TemplatesPage } from "./pages/TemplatesPage";
import { WorkLogPage } from "./pages/WorkLogPage";
import { SettingsPage } from "./pages/SettingsPage";
import { DisplayPage } from "./pages/DisplayPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <NavLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "registration", element: <RegistrationPage /> },
      { path: "summary", element: <SummaryPage /> },
      { path: "live-board", element: <LiveBoardPage /> },
      { path: "cards", element: <CardManagementPage /> },
      { path: "templates", element: <TemplatesPage /> },
      { path: "work-logs", element: <WorkLogPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "/display", element: <DisplayPage /> },
    ],
  },
]);
