import { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network/standalone';
import { getGraphVisualization } from '../utils/api';

const KARAKA_COLORS = {
  KARTA: '#ef4444',        // red
  KARMA: '#3b82f6',        // blue
  SAMPRADANA: '#22c55e',   // green
  KARANA: '#eab308',       // yellow
  ADHIKARANA: '#a855f7',   // purple
  APADANA: '#f97316'       // orange
};

const GraphVisualization = () => {
  const containerRef = useRef(null);
  const networkRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAndRenderGraph = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getGraphVisualization();
      renderGraph(data);
    } catch (err) {
      setError(err.message || 'Failed to load graph');
      console.error('Graph fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderGraph = (data) => {
    if (!containerRef.current) return;

    const nodes = data.nodes.map(node => ({
      id: node.id,
      label: node.label,
      shape: node.type === 'Entity' ? 'circle' : 'box',
      color: node.type === 'Entity' ? '#60a5fa' : '#fbbf24',
      font: { color: '#ffffff' },
      title: formatNodeTooltip(node)
    }));

    const edges = data.edges.map(edge => ({
      from: edge.from,
      to: edge.to,
      label: edge.label,
      color: { color: KARAKA_COLORS[edge.label] || '#999999' },
      arrows: 'to',
      font: { size: 10, align: 'middle' },
      title: formatEdgeTooltip(edge)
    }));

    const graphData = { nodes, edges };

    const options = {
      nodes: {
        borderWidth: 2,
        borderWidthSelected: 3,
        size: 25,
        font: {
          size: 14,
          color: '#ffffff'
        }
      },
      edges: {
        width: 2,
        smooth: {
          type: 'continuous'
        }
      },
      physics: {
        enabled: true,
        stabilization: {
          iterations: 200
        },
        barnesHut: {
          gravitationalConstant: -2000,
          springConstant: 0.001,
          springLength: 200
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 100
      }
    };

    if (networkRef.current) {
      networkRef.current.destroy();
    }

    networkRef.current = new Network(containerRef.current, graphData, options);
  };

  const formatNodeTooltip = (node) => {
    let tooltip = `<strong>${node.label}</strong><br/>Type: ${node.type}`;
    
    if (node.document_ids && node.document_ids.length > 0) {
      tooltip += `<br/>Documents: ${node.document_ids.join(', ')}`;
    }
    
    if (node.document_id) {
      tooltip += `<br/>Document: ${node.document_id}`;
    }
    
    if (node.aliases && node.aliases.length > 0) {
      tooltip += `<br/>Aliases: ${node.aliases.join(', ')}`;
    }
    
    return tooltip;
  };

  const formatEdgeTooltip = (edge) => {
    let tooltip = `<strong>${edge.label}</strong>`;
    
    if (edge.confidence) {
      tooltip += `<br/>Confidence: ${(edge.confidence * 100).toFixed(1)}%`;
    }
    
    if (edge.document_id) {
      tooltip += `<br/>Document: ${edge.document_id}`;
    }
    
    return tooltip;
  };

  useEffect(() => {
    fetchAndRenderGraph();

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
  }, []);

  return (
    <div className="graph-visualization">
      <div className="graph-header">
        <h2>Knowledge Graph</h2>
        <button 
          onClick={fetchAndRenderGraph}
          disabled={loading}
          className="refresh-btn"
        >
          {loading ? 'Loading...' : 'Refresh Graph'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div 
        ref={containerRef} 
        className="graph-container"
        style={{ height: '600px', border: '1px solid #ddd' }}
      />

      <div className="karaka-legend">
        <h3>Kāraka Relationships</h3>
        <div className="legend-items">
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: KARAKA_COLORS.KARTA }}></span>
            <span className="legend-label">KARTA (Agent)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: KARAKA_COLORS.KARMA }}></span>
            <span className="legend-label">KARMA (Patient/Object)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: KARAKA_COLORS.SAMPRADANA }}></span>
            <span className="legend-label">SAMPRADANA (Recipient)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: KARAKA_COLORS.KARANA }}></span>
            <span className="legend-label">KARANA (Instrument)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: KARAKA_COLORS.ADHIKARANA }}></span>
            <span className="legend-label">ADHIKARANA (Location)</span>
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: KARAKA_COLORS.APADANA }}></span>
            <span className="legend-label">APADANA (Source)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GraphVisualization;
