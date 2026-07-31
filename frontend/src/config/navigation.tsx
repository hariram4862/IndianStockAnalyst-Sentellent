import {
    LayoutDashboard,
    Bot,
    Star,
    LineChart,
    User,
    Settings,
} from "lucide-react";

export const sidebarItems = [
    {
        title: "Dashboard",
        href: "/",
        icon: LayoutDashboard,
    },
    {
        title: "AI Analyst",
        href: "/ai",
        icon: Bot,
    },
    {
        title: "Watchlist",
        href: "/watchlist",
        icon: Star,
    },
    {
        title: "Stocks",
        href: "/stocks",
        icon: LineChart,
    },
    {
        title: "Profile",
        href: "/profile",
        icon: User,
    },
    {
        title: "Settings",
        href: "/settings",
        icon: Settings,
    },
];