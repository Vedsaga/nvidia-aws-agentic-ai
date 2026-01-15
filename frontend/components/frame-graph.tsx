"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { Button } from "@/components/ui/button";

// Dynamic import to avoid SSR issues with Canvas
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
    loading: () => (
        <div className="flex h-full w-full items-center justify-center bg-zinc-900 text-zinc-400">
            Loading Graph...
        </div>
    ),
});

interface GraphNode {
    id: string;
    label: string;
    node_type?: string;
    x?: number;
    y?: number;
    color?: string;
    [key: string]: unknown;
}

interface GraphLink {
    source: string | GraphNode;
    target: string | GraphNode;
    label: string;
    [key: string]: unknown;
}

interface FrameGraphProps {
    nodes: GraphNode[];
    edges: GraphLink[];
    width?: number;
    height?: number;
}

// Custom hook to detect container dimensions
function useContainerDimensions(ref: React.RefObject<HTMLDivElement | null>) {
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

    useEffect(() => {
        const getDimensions = () => ({
            width: ref.current?.offsetWidth ?? 0,
            height: ref.current?.offsetHeight ?? 0,
        });

        const handleResize = () => {
            setDimensions(getDimensions());
        };

        if (ref.current) {
            setDimensions(getDimensions());
        }

        window.addEventListener("resize", handleResize);
        return () => window.removeEventListener("resize", handleResize);
    }, [ref]);

    return dimensions;
}

const getNodeColor = (type?: string) => {
    const t = type?.toLowerCase() ?? "";
    if (t.includes("agent") || t.includes("karta") || t.includes("kartā")) return "#ef4444"; // Red
    if (t.includes("object") || t.includes("karma")) return "#3b82f6"; // Blue
    if (t.includes("action") || t.includes("verb") || t.includes("root")) return "#eab308"; // Yellow
    if (t.includes("recipient") || t.includes("sampradana")) return "#a855f7"; // Purple
    if (t.includes("source") || t.includes("apadana")) return "#ec4899"; // Pink
    if (t.includes("location") || t.includes("time") || t.includes("adhikarana")) return "#10b981"; // Green
    return "#9ca3af"; // Grey
};

export default function FrameGraph({ nodes, edges }: FrameGraphProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const graphRef = useRef<any>(null);
    const { width, height } = useContainerDimensions(containerRef);
    const [isDark, setIsDark] = useState(false);

    // Detect dark mode (simple version, relies on 'dark' class on documentElement or body)
    useEffect(() => {
        const checkDark = () => {
            setIsDark(document.documentElement.classList.contains("dark"));
        };
        checkDark();
        const observer = new MutationObserver(checkDark);
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
        return () => observer.disconnect();
    }, []);

    const processedData = useMemo(() => {
        // Clone to avoid mutation issues with the library
        return {
            nodes: nodes.map((n) => ({ ...n, color: getNodeColor(n.node_type), val: n.node_type?.includes("root") ? 20 : 5 })),
            links: edges.map((e) => ({ ...e })),
        };
    }, [nodes, edges]);

    const handleZoomIn = () => {
        graphRef.current?.zoom(graphRef.current.zoom() * 1.2, 400);
    };

    const handleZoomOut = () => {
        graphRef.current?.zoom(graphRef.current.zoom() / 1.2, 400);
    };

    const handleFitView = () => {
        graphRef.current?.zoomToFit(400, 20);
    };

    return (
        <div className="relative h-full w-full overflow-hidden rounded-lg bg-zinc-950 shadow-inner" ref={containerRef}>
            <div className="absolute right-4 top-4 z-10 flex flex-col gap-2">
                <Button variant="secondary" size="icon" className="h-8 w-8 bg-zinc-800 text-zinc-100 hover:bg-zinc-700" onClick={handleZoomIn}>
                    <ZoomIn className="h-4 w-4" />
                </Button>
                <Button variant="secondary" size="icon" className="h-8 w-8 bg-zinc-800 text-zinc-100 hover:bg-zinc-700" onClick={handleZoomOut}>
                    <ZoomOut className="h-4 w-4" />
                </Button>
                <Button variant="secondary" size="icon" className="h-8 w-8 bg-zinc-800 text-zinc-100 hover:bg-zinc-700" onClick={handleFitView}>
                    <Maximize2 className="h-4 w-4" />
                </Button>
            </div>

            {width > 0 && height > 0 && (
                <ForceGraph2D
                    ref={graphRef}
                    width={width}
                    height={height}
                    graphData={processedData}
                    backgroundColor={isDark ? "#09090b" : "#18181b"} // Always darkish theme for graph usually looks better, or match theme
                    nodeLabel="label"
                    nodeRelSize={6}
                    linkColor={() => "#52525b"}
                    linkDirectionalArrowLength={3.5}
                    linkDirectionalArrowRelPos={1}
                    linkWidth={1.5}
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    nodeCanvasObject={(node: any, ctx, globalScale) => {
                        const label = node.label;
                        const fontSize = 12 / globalScale;
                        ctx.font = `${fontSize}px Sans-Serif`;
                        // Draw circle
                        ctx.beginPath();
                        ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
                        ctx.fillStyle = node.color || "#fff";
                        ctx.fill();

                        // Draw label
                        ctx.textAlign = "center";
                        ctx.textBaseline = "middle";
                        ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
                        ctx.fillText(label, node.x, node.y + 8);
                    }}
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    onNodeDragEnd={(node: any) => {
                        node.fx = node.x;
                        node.fy = node.y;
                    }}
                />
            )}
        </div>
    );
}
