"""
Package entity - Represents a software package or tool
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from enum import Enum
import uuid

from ..value_objects.price import Price


class PackageType(Enum):
    """Types of software packages"""
    LIBRARY = "library"
    FRAMEWORK = "framework"
    TOOL = "tool"
    APPLICATION = "application"
    PLUGIN = "plugin"
    EXTENSION = "extension"
    SDK = "sdk"
    API = "api"
    SERVICE = "service"


class PackageStatus(Enum):
    """Package status"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    BETA = "beta"
    ALPHA = "alpha"
    EXPERIMENTAL = "experimental"


class LicenseType(Enum):
    """Software license types"""
    MIT = "mit"
    APACHE_2 = "apache-2.0"
    GPL_V3 = "gpl-3.0"
    BSD_3_CLAUSE = "bsd-3-clause"
    ISC = "isc"
    UNLICENSE = "unlicense"
    PROPRIETARY = "proprietary"
    COMMERCIAL = "commercial"
    FREEMIUM = "freemium"
    OPEN_SOURCE = "open-source"


@dataclass
class PackageVersion:
    """Represents a version of a package"""
    version: str
    release_date: datetime
    changelog: Optional[str] = None
    download_url: Optional[str] = None
    is_stable: bool = True
    is_latest: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'version': self.version,
            'release_date': self.release_date.isoformat(),
            'changelog': self.changelog,
            'download_url': self.download_url,
            'is_stable': self.is_stable,
            'is_latest': self.is_latest
        }


@dataclass
class PackageDependency:
    """Represents a package dependency"""
    name: str
    version_requirement: str
    is_optional: bool = False
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'version_requirement': self.version_requirement,
            'is_optional': self.is_optional,
            'description': self.description
        }


@dataclass
class Package:
    """
    Package entity representing a software package or tool.
    
    This is a mutable entity (not frozen) as packages can change state.
    """
    # Identity
    package_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slug: str = ""
    
    # Basic information
    description: str = ""
    long_description: Optional[str] = None
    package_type: PackageType = PackageType.LIBRARY
    status: PackageStatus = PackageStatus.ACTIVE
    
    # Categorization
    category: str = ""
    subcategory: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # Pricing and licensing
    price: Price = field(default_factory=Price.zero)
    license_type: LicenseType = LicenseType.OPEN_SOURCE
    license_url: Optional[str] = None
    
    # Technical details
    programming_languages: List[str] = field(default_factory=list)
    platforms: List[str] = field(default_factory=list)  # Windows, macOS, Linux, etc.
    architectures: List[str] = field(default_factory=list)  # x86, x64, ARM, etc.
    
    # Versions and releases
    current_version: str = "1.0.0"
    versions: List[PackageVersion] = field(default_factory=list)
    
    # Dependencies
    dependencies: List[PackageDependency] = field(default_factory=list)
    dev_dependencies: List[PackageDependency] = field(default_factory=list)
    
    # Repository and links
    repository_url: Optional[str] = None
    homepage_url: Optional[str] = None
    documentation_url: Optional[str] = None
    download_url: Optional[str] = None
    
    # Maintainer information
    author: Optional[str] = None
    author_email: Optional[str] = None
    maintainers: List[str] = field(default_factory=list)
    organization: Optional[str] = None
    
    # Statistics
    download_count: int = 0
    star_count: int = 0
    fork_count: int = 0
    issue_count: int = 0
    
    # Quality metrics
    rating: Optional[float] = None
    review_count: int = 0
    security_score: Optional[float] = None
    maintenance_score: Optional[float] = None
    popularity_score: Optional[float] = None
    
    # Features and capabilities
    features: List[str] = field(default_factory=list)
    supported_formats: List[str] = field(default_factory=list)
    integrations: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_release_at: Optional[datetime] = None
    
    # Additional metadata
    size_mb: Optional[float] = None
    installation_instructions: Optional[str] = None
    usage_examples: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate package data after initialization"""
        if not self.name:
            raise ValueError("Package name cannot be empty")
        
        if not self.slug:
            self.slug = self._generate_slug(self.name)
        
        if not self.description:
            raise ValueError("Package description cannot be empty")
        
        if self.rating is not None and (self.rating < 0 or self.rating > 5):
            raise ValueError("Rating must be between 0 and 5")
        
        if self.security_score is not None and (self.security_score < 0 or self.security_score > 1):
            raise ValueError("Security score must be between 0 and 1")
    
    @staticmethod
    def _generate_slug(name: str) -> str:
        """Generate URL-friendly slug from package name"""
        import re
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug
    
    @property
    def is_free(self) -> bool:
        """Check if package is free"""
        return self.price.is_free()
    
    @property
    def is_open_source(self) -> bool:
        """Check if package is open source"""
        open_source_licenses = {
            LicenseType.MIT, LicenseType.APACHE_2, LicenseType.GPL_V3,
            LicenseType.BSD_3_CLAUSE, LicenseType.ISC, LicenseType.UNLICENSE,
            LicenseType.OPEN_SOURCE
        }
        return self.license_type in open_source_licenses
    
    @property
    def is_commercial(self) -> bool:
        """Check if package is commercial"""
        return self.license_type in {LicenseType.PROPRIETARY, LicenseType.COMMERCIAL}
    
    @property
    def is_stable(self) -> bool:
        """Check if package is stable (not beta/alpha/experimental)"""
        return self.status == PackageStatus.ACTIVE
    
    @property
    def is_maintained(self) -> bool:
        """Check if package is actively maintained"""
        if self.last_release_at is None:
            return False
        
        # Consider maintained if released within last year
        days_since_release = (datetime.utcnow() - self.last_release_at).days
        return days_since_release <= 365
    
    @property
    def is_popular(self) -> bool:
        """Check if package is popular (high download/star count)"""
        return self.download_count > 10000 or self.star_count > 100
    
    @property
    def has_good_rating(self) -> bool:
        """Check if package has good rating (4.0+)"""
        return self.rating is not None and self.rating >= 4.0
    
    @property
    def maturity_level(self) -> str:
        """Get package maturity level"""
        if self.status in {PackageStatus.ALPHA, PackageStatus.EXPERIMENTAL}:
            return "experimental"
        elif self.status == PackageStatus.BETA:
            return "beta"
        elif self.status == PackageStatus.DEPRECATED:
            return "deprecated"
        elif self.is_maintained and self.download_count > 1000:
            return "mature"
        else:
            return "stable"
    
    @property
    def quality_score(self) -> float:
        """Calculate overall quality score (0.0 to 1.0)"""
        score = 0.0
        factors = 0
        
        # Rating factor (weight: 0.3)
        if self.rating is not None:
            score += (self.rating / 5.0) * 0.3
            factors += 0.3
        
        # Security score factor (weight: 0.2)
        if self.security_score is not None:
            score += self.security_score * 0.2
            factors += 0.2
        
        # Maintenance factor (weight: 0.2)
        if self.maintenance_score is not None:
            score += self.maintenance_score * 0.2
        elif self.is_maintained:
            score += 0.8 * 0.2
        factors += 0.2
        
        # Popularity factor (weight: 0.15)
        if self.popularity_score is not None:
            score += self.popularity_score * 0.15
        elif self.is_popular:
            score += 0.7 * 0.15
        factors += 0.15
        
        # Documentation factor (weight: 0.15)
        has_docs = bool(self.documentation_url or self.long_description)
        score += (0.8 if has_docs else 0.2) * 0.15
        factors += 0.15
        
        return score / factors if factors > 0 else 0.0
    
    def add_version(self, version: str, release_date: Optional[datetime] = None,
                   changelog: Optional[str] = None, is_stable: bool = True) -> None:
        """Add a new version"""
        if release_date is None:
            release_date = datetime.utcnow()
        
        # Mark previous latest as not latest
        for v in self.versions:
            v.is_latest = False
        
        new_version = PackageVersion(
            version=version,
            release_date=release_date,
            changelog=changelog,
            is_stable=is_stable,
            is_latest=True
        )
        
        self.versions.append(new_version)
        self.current_version = version
        self.last_release_at = release_date
        self.updated_at = datetime.utcnow()
    
    def add_dependency(self, name: str, version_requirement: str,
                      is_optional: bool = False, description: Optional[str] = None) -> None:
        """Add a dependency"""
        dependency = PackageDependency(
            name=name,
            version_requirement=version_requirement,
            is_optional=is_optional,
            description=description
        )
        self.dependencies.append(dependency)
        self.updated_at = datetime.utcnow()
    
    def add_feature(self, feature: str) -> None:
        """Add a feature"""
        if feature not in self.features:
            self.features.append(feature)
            self.updated_at = datetime.utcnow()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.utcnow()
    
    def update_stats(self, download_count: Optional[int] = None,
                    star_count: Optional[int] = None,
                    fork_count: Optional[int] = None,
                    issue_count: Optional[int] = None) -> None:
        """Update package statistics"""
        if download_count is not None:
            self.download_count = download_count
        if star_count is not None:
            self.star_count = star_count
        if fork_count is not None:
            self.fork_count = fork_count
        if issue_count is not None:
            self.issue_count = issue_count
        
        self.updated_at = datetime.utcnow()
    
    def update_rating(self, rating: float, review_count: Optional[int] = None) -> None:
        """Update package rating"""
        if rating < 0 or rating > 5:
            raise ValueError("Rating must be between 0 and 5")
        
        self.rating = rating
        if review_count is not None:
            self.review_count = review_count
        
        self.updated_at = datetime.utcnow()
    
    def deprecate(self, reason: Optional[str] = None) -> None:
        """Mark package as deprecated"""
        self.status = PackageStatus.DEPRECATED
        if reason and self.long_description:
            self.long_description += f"\n\n**DEPRECATED**: {reason}"
        self.updated_at = datetime.utcnow()
    
    def archive(self) -> None:
        """Archive the package"""
        self.status = PackageStatus.ARCHIVED
        self.updated_at = datetime.utcnow()
    
    def matches_query(self, query: str) -> bool:
        """Check if package matches search query"""
        query_lower = query.lower()
        
        # Check name and description
        if (query_lower in self.name.lower() or 
            query_lower in self.description.lower()):
            return True
        
        # Check tags and keywords
        if any(query_lower in tag.lower() for tag in self.tags):
            return True
        
        if any(query_lower in keyword.lower() for keyword in self.keywords):
            return True
        
        # Check features
        if any(query_lower in feature.lower() for feature in self.features):
            return True
        
        return False
    
    def supports_platform(self, platform: str) -> bool:
        """Check if package supports a platform"""
        return platform.lower() in [p.lower() for p in self.platforms]
    
    def supports_language(self, language: str) -> bool:
        """Check if package supports a programming language"""
        return language.lower() in [l.lower() for l in self.programming_languages]
    
    def has_integration(self, integration: str) -> bool:
        """Check if package has specific integration"""
        return integration.lower() in [i.lower() for i in self.integrations]
    
    def get_latest_version(self) -> Optional[PackageVersion]:
        """Get the latest version"""
        for version in self.versions:
            if version.is_latest:
                return version
        return None
    
    def get_stable_versions(self) -> List[PackageVersion]:
        """Get all stable versions"""
        return [v for v in self.versions if v.is_stable]
    
    def to_dict(self, include_versions: bool = True) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        data = {
            'package_id': self.package_id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'long_description': self.long_description,
            'package_type': self.package_type.value,
            'status': self.status.value,
            'category': self.category,
            'subcategory': self.subcategory,
            'tags': self.tags,
            'keywords': self.keywords,
            'price': self.price.to_dict(),
            'license_type': self.license_type.value,
            'license_url': self.license_url,
            'programming_languages': self.programming_languages,
            'platforms': self.platforms,
            'architectures': self.architectures,
            'current_version': self.current_version,
            'repository_url': self.repository_url,
            'homepage_url': self.homepage_url,
            'documentation_url': self.documentation_url,
            'download_url': self.download_url,
            'author': self.author,
            'author_email': self.author_email,
            'maintainers': self.maintainers,
            'organization': self.organization,
            'statistics': {
                'download_count': self.download_count,
                'star_count': self.star_count,
                'fork_count': self.fork_count,
                'issue_count': self.issue_count,
                'review_count': self.review_count
            },
            'quality': {
                'rating': self.rating,
                'security_score': self.security_score,
                'maintenance_score': self.maintenance_score,
                'popularity_score': self.popularity_score,
                'quality_score': self.quality_score
            },
            'features': self.features,
            'supported_formats': self.supported_formats,
            'integrations': self.integrations,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_release_at': self.last_release_at.isoformat() if self.last_release_at else None,
            'size_mb': self.size_mb,
            'installation_instructions': self.installation_instructions,
            'usage_examples': self.usage_examples,
            'metadata': {
                'is_free': self.is_free,
                'is_open_source': self.is_open_source,
                'is_commercial': self.is_commercial,
                'is_stable': self.is_stable,
                'is_maintained': self.is_maintained,
                'is_popular': self.is_popular,
                'has_good_rating': self.has_good_rating,
                'maturity_level': self.maturity_level
            }
        }
        
        if include_versions:
            data['versions'] = [v.to_dict() for v in self.versions]
            data['dependencies'] = [d.to_dict() for d in self.dependencies]
            data['dev_dependencies'] = [d.to_dict() for d in self.dev_dependencies]
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Package':
        """Create Package from dictionary"""
        # Parse timestamps
        created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
        
        last_release_at = None
        if data.get('last_release_at'):
            last_release_at = datetime.fromisoformat(data['last_release_at'].replace('Z', '+00:00'))
        
        # Parse price
        price = Price.zero()
        if data.get('price'):
            price = Price.from_dict(data['price'])
        
        # Create package
        package = cls(
            package_id=data['package_id'],
            name=data['name'],
            slug=data.get('slug', ''),
            description=data['description'],
            long_description=data.get('long_description'),
            package_type=PackageType(data.get('package_type', 'library')),
            status=PackageStatus(data.get('status', 'active')),
            category=data.get('category', ''),
            subcategory=data.get('subcategory'),
            tags=data.get('tags', []),
            keywords=data.get('keywords', []),
            price=price,
            license_type=LicenseType(data.get('license_type', 'open-source')),
            license_url=data.get('license_url'),
            programming_languages=data.get('programming_languages', []),
            platforms=data.get('platforms', []),
            architectures=data.get('architectures', []),
            current_version=data.get('current_version', '1.0.0'),
            repository_url=data.get('repository_url'),
            homepage_url=data.get('homepage_url'),
            documentation_url=data.get('documentation_url'),
            download_url=data.get('download_url'),
            author=data.get('author'),
            author_email=data.get('author_email'),
            maintainers=data.get('maintainers', []),
            organization=data.get('organization'),
            download_count=data.get('statistics', {}).get('download_count', 0),
            star_count=data.get('statistics', {}).get('star_count', 0),
            fork_count=data.get('statistics', {}).get('fork_count', 0),
            issue_count=data.get('statistics', {}).get('issue_count', 0),
            review_count=data.get('statistics', {}).get('review_count', 0),
            rating=data.get('quality', {}).get('rating'),
            security_score=data.get('quality', {}).get('security_score'),
            maintenance_score=data.get('quality', {}).get('maintenance_score'),
            popularity_score=data.get('quality', {}).get('popularity_score'),
            features=data.get('features', []),
            supported_formats=data.get('supported_formats', []),
            integrations=data.get('integrations', []),
            created_at=created_at,
            updated_at=updated_at,
            last_release_at=last_release_at,
            size_mb=data.get('size_mb'),
            installation_instructions=data.get('installation_instructions'),
            usage_examples=data.get('usage_examples', [])
        )
        
        # Add versions if present
        if data.get('versions'):
            for v_data in data['versions']:
                version = PackageVersion(
                    version=v_data['version'],
                    release_date=datetime.fromisoformat(v_data['release_date'].replace('Z', '+00:00')),
                    changelog=v_data.get('changelog'),
                    download_url=v_data.get('download_url'),
                    is_stable=v_data.get('is_stable', True),
                    is_latest=v_data.get('is_latest', False)
                )
                package.versions.append(version)
        
        # Add dependencies if present
        if data.get('dependencies'):
            for d_data in data['dependencies']:
                dependency = PackageDependency(
                    name=d_data['name'],
                    version_requirement=d_data['version_requirement'],
                    is_optional=d_data.get('is_optional', False),
                    description=d_data.get('description')
                )
                package.dependencies.append(dependency)
        
        return package
    
    def __str__(self) -> str:
        """String representation"""
        return f"Package({self.name} v{self.current_version}, {self.package_type.value})"
    
    def __eq__(self, other) -> bool:
        """Equality comparison based on package_id"""
        if not isinstance(other, Package):
            return False
        return self.package_id == other.package_id
    
    def __hash__(self) -> int:
        """Hash based on package_id"""
        return hash(self.package_id)