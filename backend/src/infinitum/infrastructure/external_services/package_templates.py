# File: src/infinitum/services/package_templates.py
"""
Package Templates Service for creating standardized shopping packages
Provides pre-defined templates for different use cases and categories
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from infinitum.infrastructure.logging_config import get_agent_logger

logger = get_agent_logger("package_templates")

class PackageTemplateService:
    """Service for managing and creating standardized shopping packages"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Any]:
        """Initialize package templates for different categories and use cases"""
        return {
            "youtube_setup": {
                "name": "YouTube Creator Setup",
                "description": "Complete setup for YouTube content creation",
                "categories": ["audio", "video", "lighting", "accessories"],
                "packages": {
                    "budget": {
                        "name": "Budget YouTube Starter Kit",
                        "price_range": "under_300",
                        "focus": ["basic_quality", "affordability", "essential_features"],
                        "requirements": ["microphone", "webcam", "basic_lighting"]
                    },
                    "professional": {
                        "name": "Professional Creator Setup",
                        "price_range": "500_1500", 
                        "focus": ["high_quality", "professional_features", "reliability"],
                        "requirements": ["professional_microphone", "4k_camera", "professional_lighting", "audio_interface"]
                    },
                    "premium": {
                        "name": "Premium Studio Setup",
                        "price_range": "above_1500",
                        "focus": ["broadcast_quality", "premium_features", "future_proof"],
                        "requirements": ["studio_microphone", "cinema_camera", "studio_lighting", "pro_audio_equipment"]
                    }
                }
            },
            
            "gaming_setup": {
                "name": "Gaming Setup",
                "description": "Complete gaming experience packages",
                "categories": ["gaming_peripherals", "audio", "accessories"],
                "packages": {
                    "casual": {
                        "name": "Casual Gamer Package",
                        "price_range": "under_400",
                        "focus": ["value", "basic_performance", "comfort"],
                        "requirements": ["gaming_headset", "mechanical_keyboard", "gaming_mouse"]
                    },
                    "competitive": {
                        "name": "Competitive Gaming Setup",
                        "price_range": "400_800",
                        "focus": ["performance", "low_latency", "competitive_advantage"],
                        "requirements": ["pro_gaming_headset", "mechanical_keyboard", "high_dpi_mouse", "gaming_monitor"]
                    },
                    "enthusiast": {
                        "name": "Gaming Enthusiast Build",
                        "price_range": "above_800",
                        "focus": ["premium_performance", "immersion", "aesthetics"],
                        "requirements": ["premium_headset", "custom_keyboard", "high_end_mouse", "curved_monitor", "rgb_accessories"]
                    }
                }
            },
            
            "work_from_home": {
                "name": "Work From Home Setup",
                "description": "Professional home office packages",
                "categories": ["office_equipment", "audio", "ergonomics"],
                "packages": {
                    "basic": {
                        "name": "Basic Home Office",
                        "price_range": "under_500",
                        "focus": ["essential_productivity", "comfort", "affordability"],
                        "requirements": ["webcam", "headset", "ergonomic_accessories"]
                    },
                    "professional": {
                        "name": "Professional Home Office",
                        "price_range": "500_1000",
                        "focus": ["productivity", "professional_appearance", "comfort"],
                        "requirements": ["4k_webcam", "noise_canceling_headset", "ring_light", "ergonomic_chair", "monitor_stand"]
                    },
                    "executive": {
                        "name": "Executive Home Office",
                        "price_range": "above_1000",
                        "focus": ["premium_quality", "executive_presence", "advanced_features"],
                        "requirements": ["premium_webcam", "wireless_headset", "professional_lighting", "standing_desk", "premium_monitor"]
                    }
                }
            },
            
            "fitness_home": {
                "name": "Home Fitness Setup",
                "description": "Complete home workout packages",
                "categories": ["fitness_equipment", "accessories", "tech"],
                "packages": {
                    "starter": {
                        "name": "Fitness Starter Kit",
                        "price_range": "under_200",
                        "focus": ["basic_equipment", "space_efficient", "affordable"],
                        "requirements": ["resistance_bands", "yoga_mat", "dumbbells"]
                    },
                    "comprehensive": {
                        "name": "Complete Home Gym",
                        "price_range": "200_800",
                        "focus": ["variety", "full_body_workout", "quality_equipment"],
                        "requirements": ["adjustable_dumbbells", "resistance_bands", "yoga_mat", "kettlebell", "fitness_tracker"]
                    },
                    "professional": {
                        "name": "Professional Home Gym",
                        "price_range": "above_800",
                        "focus": ["gym_quality", "comprehensive_training", "durability"],
                        "requirements": ["power_rack", "olympic_barbell", "weight_plates", "bench", "cardio_equipment"]
                    }
                }
            },
            
            "smart_home": {
                "name": "Smart Home Setup", 
                "description": "Intelligent home automation packages",
                "categories": ["smart_devices", "security", "entertainment"],
                "packages": {
                    "starter": {
                        "name": "Smart Home Starter",
                        "price_range": "under_300",
                        "focus": ["basic_automation", "ease_of_use", "affordability"],
                        "requirements": ["smart_speaker", "smart_bulbs", "smart_plug"]
                    },
                    "connected": {
                        "name": "Connected Home Package",
                        "price_range": "300_800", 
                        "focus": ["comprehensive_control", "security", "convenience"],
                        "requirements": ["smart_hub", "smart_lights", "smart_thermostat", "security_camera", "smart_lock"]
                    },
                    "intelligent": {
                        "name": "Intelligent Home System",
                        "price_range": "above_800",
                        "focus": ["advanced_automation", "integration", "premium_features"],
                        "requirements": ["premium_hub", "comprehensive_lighting", "climate_control", "security_system", "entertainment_integration"]
                    }
                }
            }
        }
    
    def get_template_for_query(self, query_analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get the most appropriate template based on query analysis"""
        try:
            categories = query_analysis.get("product_categories", [])
            use_case = query_analysis.get("use_case", "")
            intent = query_analysis.get("intent_analysis", "").lower()
            
            # Direct use case matching
            if "youtube" in use_case.lower() or "content" in intent:
                return self.templates.get("youtube_setup")
            elif "gaming" in use_case.lower() or "game" in intent:
                return self.templates.get("gaming_setup")
            elif "work" in use_case.lower() or "office" in intent:
                return self.templates.get("work_from_home")
            elif "fitness" in use_case.lower() or "workout" in intent:
                return self.templates.get("fitness_home")
            elif "smart" in use_case.lower() or "home automation" in intent:
                return self.templates.get("smart_home")
            
            # Category-based matching
            for template_name, template in self.templates.items():
                template_categories = template.get("categories", [])
                if any(cat in categories for cat in template_categories):
                    return template
            
            return None
            
        except Exception as e:
            logger.error(f"Error selecting template: {e}")
            return None
    
    def create_template_based_packages(self, template: Dict[str, Any], 
                                     available_products: List[Dict[str, Any]],
                                     budget_preference: str = "balanced") -> List[Dict[str, Any]]:
        """Create packages based on template structure"""
        try:
            packages = []
            template_packages = template.get("packages", {})
            
            for package_type, package_config in template_packages.items():
                # Create package based on template
                package = {
                    "name": package_config["name"],
                    "description": f"{package_config['name']} - {', '.join(package_config['focus'])}",
                    "template_type": package_type,
                    "price_range": package_config["price_range"],
                    "focus_areas": package_config["focus"],
                    "requirements": package_config["requirements"],
                    "products": self._match_products_to_requirements(
                        available_products, 
                        package_config["requirements"]
                    ),
                    "why_this_package": self._generate_template_reasoning(package_config),
                    "total_estimated_price": self._estimate_package_price(package_config["price_range"]),
                    "template_based": True
                }
                
                packages.append(package)
            
            # Sort packages based on budget preference
            return self._sort_packages_by_preference(packages, budget_preference)
            
        except Exception as e:
            logger.error(f"Error creating template-based packages: {e}")
            return []
    
    def _match_products_to_requirements(self, products: List[Dict[str, Any]], 
                                      requirements: List[str]) -> List[Dict[str, Any]]:
        """Match available products to template requirements"""
        matched_products = []
        
        for requirement in requirements:
            # Find best matching product for this requirement
            best_match = None
            best_score = 0
            
            for product in products:
                score = self._calculate_requirement_match(product, requirement)
                if score > best_score:
                    best_score = score
                    best_match = product
            
            if best_match and best_score > 0.3:  # Minimum match threshold
                product_copy = best_match.copy()
                product_copy["requirement_match"] = requirement
                product_copy["match_score"] = best_score
                matched_products.append(product_copy)
        
        return matched_products
    
    def _calculate_requirement_match(self, product: Dict[str, Any], requirement: str) -> float:
        """Calculate how well a product matches a template requirement"""
        title = product.get("title", "").lower()
        description = product.get("description", "").lower()
        
        # Create keyword mapping for requirements
        requirement_keywords = {
            "microphone": ["microphone", "mic", "audio", "recording"],
            "webcam": ["webcam", "camera", "video", "streaming"],
            "lighting": ["light", "lamp", "led", "ring light", "softbox"],
            "headset": ["headset", "headphones", "earphones", "audio"],
            "keyboard": ["keyboard", "mechanical", "gaming"],
            "mouse": ["mouse", "gaming mouse", "wireless mouse"],
            "monitor": ["monitor", "display", "screen", "lcd", "led"],
            "fitness_tracker": ["fitness", "tracker", "smartwatch", "activity"]
        }
        
        # Get keywords for this requirement
        keywords = requirement_keywords.get(requirement, [requirement.replace("_", " ")])
        
        # Calculate match score
        matches = 0
        for keyword in keywords:
            if keyword in title or keyword in description:
                matches += 1
        
        return min(matches / len(keywords), 1.0)
    
    def _generate_template_reasoning(self, package_config: Dict[str, Any]) -> str:
        """Generate reasoning for template-based package"""
        focus_areas = package_config.get("focus", [])
        price_range = package_config.get("price_range", "")
        
        reasoning = f"This package focuses on {', '.join(focus_areas)} "
        
        if "under" in price_range:
            reasoning += "while maintaining affordability and delivering excellent value for money."
        elif "above" in price_range:
            reasoning += "with premium components for the best possible experience."
        else:
            reasoning += "offering the optimal balance of features and price."
        
        return reasoning
    
    def _estimate_package_price(self, price_range: str) -> str:
        """Estimate total package price based on range"""
        price_estimates = {
            "under_200": "$150 - $200",
            "under_300": "$200 - $300", 
            "under_400": "$300 - $400",
            "under_500": "$400 - $500",
            "200_800": "$200 - $800",
            "300_800": "$300 - $800",
            "400_800": "$400 - $800",
            "500_1000": "$500 - $1,000",
            "500_1500": "$500 - $1,500",
            "above_800": "$800+",
            "above_1000": "$1,000+",
            "above_1500": "$1,500+"
        }
        
        return price_estimates.get(price_range, "Price varies")
    
    def _sort_packages_by_preference(self, packages: List[Dict[str, Any]], 
                                   preference: str) -> List[Dict[str, Any]]:
        """Sort packages based on user preference"""
        preference_order = {
            "budget": ["budget", "starter", "basic", "casual"],
            "balanced": ["professional", "comprehensive", "connected", "competitive"],
            "premium": ["premium", "executive", "intelligent", "enthusiast"]
        }
        
        order = preference_order.get(preference, preference_order["balanced"])
        
        def sort_key(package):
            template_type = package.get("template_type", "")
            try:
                return order.index(template_type)
            except ValueError:
                return len(order)  # Put unknown types at the end
        
        return sorted(packages, key=sort_key)
    
    def get_available_templates(self) -> Dict[str, Any]:
        """Get all available templates with metadata"""
        template_info = {}
        
        for template_name, template in self.templates.items():
            template_info[template_name] = {
                "name": template["name"],
                "description": template["description"],
                "categories": template["categories"],
                "package_types": list(template["packages"].keys())
            }
        
        return template_info

# Global instance
package_template_service = PackageTemplateService()