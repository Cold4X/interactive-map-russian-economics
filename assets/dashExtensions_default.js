window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, context) {
            const {
                classes,
                colorscale,
                style,
                colorProp,
                categorical,
                labels
            } = context.hideout;
            const value = feature.properties[colorProp];
            const noDataColor = '#d3d3d3';

            if (value === undefined || value === null) {
                return {
                    ...style,
                    fillColor: noDataColor,
                    fillOpacity: 0.3
                };
            }

            if (categorical === true && labels && Array.isArray(labels)) {
                const index = labels.indexOf(value);
                if (index >= 0 && index < colorscale.length) {
                    return {
                        ...style,
                        fillColor: colorscale[index],
                        fillOpacity: 0.7,
                        weight: 2,
                        color: "#333",
                        opacity: 1
                    };
                } else {
                    return {
                        ...style,
                        fillColor: noDataColor,
                        fillOpacity: 0.3,
                        weight: 2,
                        color: "#333",
                        opacity: 1
                    };
                }
            }

            if (colorProp === "delta") {
                const numValue = Number(value);
                if (isNaN(numValue)) {
                    return {
                        ...style,
                        fillColor: noDataColor,
                        fillOpacity: 0.3
                    };
                }

                let colorIndex = 0;
                for (let i = 0; i < classes.length - 1; i++) {
                    if (numValue >= classes[i] && numValue < classes[i + 1]) {
                        colorIndex = i;
                        break;
                    }
                }

                if (numValue >= classes[classes.length - 1]) {
                    colorIndex = colorscale.length - 1;
                }

                if (numValue < classes[0]) {
                    colorIndex = 0;
                }

                const finalColor = colorscale[colorIndex];
                return {
                    ...style,
                    fillColor: finalColor,
                    fillOpacity: 0.7
                };
            }

            if (colorProp === "none") {
                return style;
            }

            const numValue = Number(value);
            if (isNaN(numValue)) {
                return {
                    ...style,
                    fillColor: noDataColor,
                    fillOpacity: 0.3
                };
            }

            let colorIndex = -1;
            for (let i = 0; i < classes.length - 1; i++) {
                if (numValue >= classes[i] && numValue < classes[i + 1]) {
                    colorIndex = i;
                    break;
                }
            }

            if (colorIndex === -1 && numValue >= classes[classes.length - 1]) {
                colorIndex = colorscale.length - 1;
            }

            if (numValue < classes[0]) {
                colorIndex = 0;
            }

            if (colorIndex >= 0 && colorIndex < colorscale.length) {
                return {
                    ...style,
                    fillColor: colorscale[colorIndex],
                    fillOpacity: 0.7,
                    weight: 2,
                    color: "#333",
                    opacity: 1
                };
            }

            return {
                ...style,
                fillColor: noDataColor,
                fillOpacity: 0.3
            };
        }
    }
});