#!/usr/bin/env python3
# thoth-storages
# Copyright(C) 2019 Fridolin Pokorny
#
# This program is free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Models for SQL based database."""

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Float
from sqlalchemy import DateTime
from sqlalchemy import Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ENUM

from sqlalchemy import UniqueConstraint
from sqlalchemy import Index

from .models_base import BaseExtension
from .models_base import Base
from .models_base import get_python_package_version_index_combinations


# Environment type used in package-extract as a flag as well as in software environment records.
_ENVIRONMENT_TYPE_ENUM = ENUM("RUNTIME", "BUILDTIME", name="environment_type", create_type=True)


class PythonPackageVersion(Base, BaseExtension):
    """Representation of a Python package version running on a specific software environment."""

    __tablename__ = "python_package_version"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)

    package_name = Column(String(256), nullable=False)
    package_version = Column(String(256), nullable=False)
    # Nullable if we have unparseable entries or entries comming from package-extract where we
    # were unable to detect these entries.
    os_name = Column(String(256), nullable=True)
    os_version = Column(String(256), nullable=True)
    python_version = Column(String(256), nullable=True)
    entity_id = Column(Integer, ForeignKey("python_package_version_entity.id", ondelete="CASCADE"), nullable=False)
    # Null if cannot parse.
    python_package_index_id = Column(Integer, ForeignKey("python_package_index.id", ondelete="CASCADE"), nullable=True)

    dependencies = relationship("DependsOn", back_populates="version")
    package_extract_runs = relationship("Identified", back_populates="python_package_version")
    solvers = relationship("Solved", back_populates="version")
    python_artifacts = relationship("HasArtifact", back_populates="python_package_version")
    entity = relationship("PythonPackageVersionEntity", back_populates="python_package_versions")
    index = relationship("PythonPackageIndex", back_populates="python_package_versions")

    python_software_stacks = relationship("PythonRequirementsLock", back_populates="python_package_version")

    __table_args__ = tuple(
        get_python_package_version_index_combinations(index_as_property=False)
        + [
            UniqueConstraint(
                "package_name", "package_version", "python_package_index_id", "os_name", "os_version", "python_version"
            ),
            Index("python_package_version_idx", "package_name", "package_version", "python_package_index_id"),
        ]
    )


class HasArtifact(Base, BaseExtension):
    """The given package has the given artifact."""

    __tablename__ = "has_artifact"

    id = Column(Integer, primary_key=True, autoincrement=True)

    python_package_version_id = Column(
        Integer, ForeignKey("python_package_version.id", ondelete="CASCADE"), primary_key=True
    )
    python_artifact_id = Column(Integer, ForeignKey("python_artifact.id", ondelete="CASCADE"), primary_key=True)

    python_package_version = relationship("PythonPackageVersion", back_populates="python_artifacts")
    python_artifact = relationship("PythonArtifact", back_populates="python_package_versions")


class Solved(Base, BaseExtension):
    """A solver solved a package-version."""

    __tablename__ = "solved"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    datetime = Column(DateTime(timezone=False), nullable=False)
    document_id = Column(String(128), nullable=False)
    duration = Column(Integer, nullable=True)  # nullable for now...

    error = Column(Boolean, default=False, nullable=False)
    error_unparseable = Column(Boolean, default=False, nullable=False)
    error_unsolvable = Column(Boolean, default=False, nullable=False)
    is_provided = Column(Boolean)

    ecosystem_solver_id = Column(Integer, ForeignKey("ecosystem_solver.id", ondelete="CASCADE"), primary_key=True)
    version_id = Column(Integer, ForeignKey("python_package_version.id", ondelete="CASCADE"), primary_key=True)

    ecosystem_solver = relationship("EcosystemSolver", back_populates="versions")
    version = relationship("PythonPackageVersion", back_populates="solvers")

    __table_args__ = (
        Index("solver_document_id_idx", "document_id"),
    )


class PythonPackageVersionEntity(Base, BaseExtension):
    """Representation of a Python package not running in any environment."""

    __tablename__ = "python_package_version_entity"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)

    package_name = Column(String(256), nullable=False)
    # Nullable if we cannot resolve.
    package_version = Column(String(256), nullable=True)
    # Nullable if coming from user or cross-index resolution.

    python_package_index_id = Column(Integer, ForeignKey("python_package_index.id", ondelete="CASCADE"), nullable=True)

    versions = relationship("DependsOn", back_populates="entity")
    package_analyzer_runs = relationship("PackageAnalyzerRun", back_populates="input_python_package_version_entity")
    cves = relationship("HasVulnerability", back_populates="python_package_version_entity")
    # inspection_software_stacks = relationship("PythonSoftwareStack", back_populates="python_package_version_entity")
    # user_software_stacks = relationship("PythonSoftwareStack", back_populates="python_package_version_entity")
    index = relationship("PythonPackageIndex", back_populates="python_package_version_entities")
    python_package_versions = relationship("PythonPackageVersion", back_populates="entity")

    __table_args__ = (
        UniqueConstraint("package_name", "package_version", "python_package_index_id"),
        Index(
            "python_package_version_entity_idx",
            "package_name",
            "package_version",
            "python_package_index_id",
            unique=True,
        ),
    )


class DependsOn(Base, BaseExtension):
    """Dependency of a Python package version."""

    __tablename__ = "depends_on"

    id = Column(Integer, primary_key=True, autoincrement=True)

    entity_id = Column(Integer, ForeignKey("python_package_version_entity.id", ondelete="CASCADE"), primary_key=True)
    version_id = Column(Integer, ForeignKey("python_package_version.id", ondelete="CASCADE"), primary_key=True)

    version_range = Column(String(128))

    entity = relationship("PythonPackageVersionEntity", back_populates="versions")
    version = relationship("PythonPackageVersion", back_populates="dependencies")

    __table_args__ = (
        UniqueConstraint("entity_id", "version_id", "version_range"),
        Index("depends_on_idx", "entity_id", "version_id", "version_range"),
        Index("depends_on_version_range_idx", "entity_id", "version_id", "version_range"),
    )


class EcosystemSolver(Base, BaseExtension):
    """Record for an ecosystem solver."""

    __tablename__ = "ecosystem_solver"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ecosystem = Column(String(256), nullable=False)
    solver_name = Column(String(256), nullable=False)
    solver_version = Column(String(16), nullable=False)
    os_name = Column(String(128), nullable=False)
    os_version = Column(String(8), nullable=False)
    python_version = Column(String(8), nullable=False)

    versions = relationship("Solved", back_populates="ecosystem_solver")

    __table_args__ = (
        UniqueConstraint("ecosystem", "solver_name", "solver_version", "os_name", "os_version", "python_version"),
        Index(
            "ecosystem_solver_idx",
            "ecosystem",
            "solver_name",
            "solver_version",
            "os_name",
            "os_version",
            "python_version",
            unique=True,
        ),
    )


class PackageExtractRun(Base, BaseExtension):
    """A class representing a single package-extract (image analysis) run."""

    __tablename__ = "package_extract_run"

    id = Column(Integer, primary_key=True, autoincrement=True)

    package_extract_name = Column(String(256), nullable=False)
    package_extract_version = Column(String(256), nullable=False)
    analysis_document_id = Column(String(256), nullable=False)
    datetime = Column(DateTime, nullable=False)
    environment_type = Column(_ENVIRONMENT_TYPE_ENUM, nullable=False)
    origin = Column(String(256), nullable=True)
    debug = Column(Boolean, nullable=False, default=False)
    package_extract_error = Column(Boolean, nullable=False, default=False)
    # An image tag which was used during image analysis. As this tag can change (e.g. latest is always changing
    # on new builds), it's part of this class instead of Runtime/Buildtime environment to keep correct
    # linkage for same container images.
    image_tag = Column(String(256), nullable=False)
    # Duration in seconds.
    duration = Column(Integer, nullable=True)
    # Entries parsed from /etc/os-release
    os_name = Column(String(256), nullable=False)
    os_id = Column(String(256), nullable=False)
    os_version_id = Column(String(256), nullable=False)
    software_environment_id = Column(Integer, ForeignKey("software_environment.id", ondelete="CASCADE"), nullable=False)

    found_python_files = relationship("FoundPythonFile", back_populates="package_extract_run")
    found_rpms = relationship("FoundRPM", back_populates="package_extract_run")
    found_debs = relationship("FoundDeb", back_populates="package_extract_run")
    python_package_version_entities = relationship("Identified", back_populates="package_extract_run")
    software_environment = relationship("SoftwareEnvironment", back_populates="package_extract_runs")
    versioned_symbols = relationship("DetectedSymbol", back_populates="package_extract_run")


class FoundPythonFile(Base, BaseExtension):
    """State a package extract run found a Python file."""

    __tablename__ = "found_python_file"

    id = Column(Integer, primary_key=True, autoincrement=True)

    file = Column(String(256), nullable=False)

    python_file_digest_id = Column(Integer, ForeignKey("python_file_digest.id", ondelete="CASCADE"), primary_key=True)
    package_extract_run_id = Column(Integer, ForeignKey("package_extract_run.id", ondelete="CASCADE"), primary_key=True)

    python_file_digest = relationship("PythonFileDigest", back_populates="package_extract_runs")
    package_extract_run = relationship("PackageExtractRun", back_populates="found_python_files")


class FoundRPM(Base, BaseExtension):
    """State a package extract run found an RPM package."""

    __tablename__ = "found_rpm"

    id = Column(Integer, primary_key=True, autoincrement=True)

    rpm_package_version_id = Column(Integer, ForeignKey("rpm_package_version.id", ondelete="CASCADE"), primary_key=True)
    package_extract_run_id = Column(Integer, ForeignKey("package_extract_run.id", ondelete="CASCADE"), primary_key=True)

    rpm_package_version = relationship("RPMPackageVersion", back_populates="package_extract_runs")
    package_extract_run = relationship("PackageExtractRun", back_populates="found_rpms")


class FoundDeb(Base, BaseExtension):
    """State a package extract run found a Debian package."""

    __tablename__ = "found_deb"

    id = Column(Integer, primary_key=True, autoincrement=True)

    deb_package_version_id = Column(Integer, ForeignKey("deb_package_version.id", ondelete="CASCADE"), primary_key=True)
    package_extract_run_id = Column(Integer, ForeignKey("package_extract_run.id", ondelete="CASCADE"), primary_key=True)

    deb_package_version = relationship("DebPackageVersion", back_populates="package_extract_runs")
    package_extract_run = relationship("PackageExtractRun", back_populates="found_debs")


class PythonPackageRequirement(Base, BaseExtension):
    """A requirement as stated by a software stack."""

    __tablename__ = "python_package_requirement"

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(256), nullable=False)
    version_range = Column(String(256), nullable=False)
    develop = Column(Boolean, nullable=False)
    python_package_index_id = Column(Integer, ForeignKey("python_package_index.id", ondelete="CASCADE"), nullable=True)

    index = relationship("PythonPackageIndex", back_populates="python_package_requirements")
    python_software_stacks = relationship("PythonRequirements", back_populates="python_package_requirement")
    dependency_monkey_runs = relationship(
        "PythonDependencyMonkeyRequirements", back_populates="python_package_requirement"
    )


class CVE(Base, BaseExtension):
    """Information about a CVE."""

    __tablename__ = "cve"

    id = Column(Integer, primary_key=True, autoincrement=True)

    advisory = Column(String(16384), nullable=True)
    cve_name = Column(String(256), nullable=True)
    cve_id = Column(String(256), nullable=True)
    version_range = Column(String(256), nullable=True)

    python_package_versions = relationship("HasVulnerability", back_populates="cve")


class PackageAnalyzerRun(Base, BaseExtension):
    """A class representing a single package-analyzer (package analysis) run."""

    __tablename__ = "package_analyzer_run"

    id = Column(Integer, primary_key=True, autoincrement=True)

    package_analyzer_name = Column(String(256), nullable=True)
    package_analyzer_version = Column(String(256), nullable=True)
    package_analysis_document_id = Column(String(256), nullable=False)
    datetime = Column(DateTime, nullable=False)
    debug = Column(Boolean, nullable=False, default=False)
    package_analyzer_error = Column(Boolean, nullable=False, default=False)
    duration = Column(Integer, nullable=True)
    input_python_package_version_entity_id = Column(
        Integer, ForeignKey("python_package_version_entity.id", ondelete="CASCADE")
    )

    input_python_package_version_entity = relationship(
        "PythonPackageVersionEntity", back_populates="package_analyzer_runs"
    )
    python_artifacts = relationship("Investigated", back_populates="package_analyzer_run")
    python_files = relationship("InvestigatedFile", back_populates="package_analyzer_run")


class PythonArtifact(Base, BaseExtension):
    """An artifact for a python package in a specific version."""

    __tablename__ = "python_artifact"

    id = Column(Integer, primary_key=True, autoincrement=True)

    artifact_hash_sha256 = Column(String(256), nullable=False)
    artifact_name = Column(String(256), nullable=True)
    # TODO: parse wheel specific tags to make them queryable?

    python_files = relationship("IncludedFile", back_populates="python_artifact")
    python_package_versions = relationship("HasArtifact", back_populates="python_artifact")
    package_analyzer_runs = relationship("Investigated", back_populates="python_artifact")
    versioned_symbols = relationship("RequiresSymbol", back_populates="python_artifact")


class InvestigatedFile(Base, BaseExtension):
    """A record about found file by package analyzer."""

    __tablename__ = "investigated_file"

    id = Column(Integer, primary_key=True, autoincrement=True)

    package_analyzer_run_id = Column(
        Integer, ForeignKey("package_analyzer_run.id", ondelete="CASCADE"), primary_key=True
    )
    python_file_digest_id = Column(Integer, ForeignKey("python_file_digest.id", ondelete="CASCADE"), primary_key=True)

    package_analyzer_run = relationship("PackageAnalyzerRun", back_populates="python_files")
    python_file_digest = relationship("PythonFileDigest", back_populates="package_analyzer_runs")


class Investigated(Base, BaseExtension):
    """A record about investigated Python artifact by a package analyzer."""

    __tablename__ = "investigated"

    id = Column(Integer, primary_key=True, autoincrement=True)

    package_analyzer_run_id = Column(
        Integer, ForeignKey("package_analyzer_run.id", ondelete="CASCADE"), primary_key=True
    )
    python_artifact_id = Column(Integer, ForeignKey("python_artifact.id", ondelete="CASCADE"), primary_key=True)

    package_analyzer_run = relationship("PackageAnalyzerRun", back_populates="python_artifacts")
    python_artifact = relationship("PythonArtifact", back_populates="package_analyzer_runs")


class PythonFileDigest(Base, BaseExtension):
    """A class representing a single file digests."""

    __tablename__ = "python_file_digest"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sha256 = Column(String(256), nullable=False)

    package_extract_runs = relationship("FoundPythonFile", back_populates="python_file_digest")
    package_analyzer_runs = relationship("InvestigatedFile", back_populates="python_file_digest")
    python_artifacts = relationship("IncludedFile", back_populates="python_file_digest")

    __table_args__ = (UniqueConstraint("sha256"), Index("sha256_idx", "sha256", unique=True))


class InspectionRun(Base, BaseExtension):
    """A class representing a single inspection."""

    __tablename__ = "inspection_run"

    id = Column(Integer, primary_key=True, autoincrement=True)

    inspection_document_id = Column(String(256), nullable=False, unique=True)
    datetime = Column(DateTime, nullable=True)
    amun_version = Column(String(256), nullable=True)
    build_requests_cpu = Column(Float, nullable=True)
    build_requests_memory = Column(Float, nullable=True)
    run_requests_cpu = Column(Float, nullable=True)
    run_requests_memory = Column(Float, nullable=True)
    inspection_sync_state = Column(
        ENUM("PENDING", "SYNCED", name="inspection_sync_state", create_type=True), nullable=False
    )

    build_hardware_information_id = Column(Integer, ForeignKey("hardware_information.id", ondelete="CASCADE"))
    run_hardware_information_id = Column(Integer, ForeignKey("hardware_information.id", ondelete="CASCADE"))
    build_software_environment_id = Column(Integer, ForeignKey("software_environment.id", ondelete="CASCADE"))
    run_software_environment_id = Column(Integer, ForeignKey("software_environment.id", ondelete="CASCADE"))
    dependency_monkey_run_id = Column(
        Integer, ForeignKey("dependency_monkey_run.id", ondelete="CASCADE"), nullable=True
    )

    build_hardware_information = relationship(
        "HardwareInformation", back_populates="inspection_runs_build", foreign_keys=[build_hardware_information_id]
    )
    run_hardware_information = relationship(
        "HardwareInformation", back_populates="inspection_runs_run", foreign_keys=[run_hardware_information_id]
    )

    build_software_environment = relationship(
        "SoftwareEnvironment", back_populates="inspection_runs_build", foreign_keys=[build_software_environment_id]
    )
    run_software_environment = relationship(
        "SoftwareEnvironment", back_populates="inspection_runs_run", foreign_keys=[run_software_environment_id]
    )

    dependency_monkey_run = relationship("DependencyMonkeyRun", back_populates="inspection_runs")

    inspection_software_stack_id = Column(Integer, ForeignKey("python_software_stack.id", ondelete="CASCADE"))
    inspection_software_stack = relationship("PythonSoftwareStack", back_populates="inspection_runs")

    matmul_perf_indicators = relationship("PiMatmul", back_populates="inspection_run")
    conv1d_perf_indicators = relationship("PiConv1D", back_populates="inspection_run")
    conv2d_perf_indicators = relationship("PiConv2D", back_populates="inspection_run")


class AdviserRun(Base, BaseExtension):
    """A class representing a single adviser run."""

    __tablename__ = "adviser_run"

    id = Column(Integer, primary_key=True, autoincrement=True)

    adviser_document_id = Column(String(256), nullable=False)
    datetime = Column(DateTime, nullable=False)
    adviser_version = Column(String(256), nullable=False)
    adviser_name = Column(String(256), nullable=False)
    count = Column(Integer, nullable=False)
    limit = Column(Integer, nullable=False)
    origin = Column(String(256), nullable=True)
    debug = Column(Boolean, nullable=False)
    limit_latest_versions = Column(Integer, nullable=False)
    adviser_error = Column(Boolean, nullable=False, default=False)
    recommendation_type = Column(
        ENUM("STABLE", "TESTING", "LATEST", name="recommendation_type", create_type=True), nullable=False
    )
    requirements_format = Column(ENUM("PIPENV", name="requirements_format", create_type=True), nullable=False)

    # Duration in seconds.
    duration = Column(Integer, nullable=True)  # XXX: nullable for now.
    advised_configuration_changes = Column(Boolean, nullable=False, default=False)
    additional_stack_info = Column(Boolean, nullable=False, default=False)

    user_run_software_environment_id = Column(Integer, ForeignKey("software_environment.id", ondelete="CASCADE"))
    user_build_software_environment_id = Column(Integer, ForeignKey("software_environment.id", ondelete="CASCADE"))

    user_software_stack_id = Column(Integer, ForeignKey("python_software_stack.id", ondelete="CASCADE"))
    user_software_stack = relationship(
        "PythonSoftwareStack", back_populates="adviser_runs", foreign_keys=[user_software_stack_id]
    )

    advised_software_stacks = relationship("Advised", back_populates="adviser_run")
    user_run_software_environment = relationship(
        "SoftwareEnvironment", back_populates="adviser_inputs_run", foreign_keys=[user_run_software_environment_id]
    )
    user_build_software_environment = relationship(
        "SoftwareEnvironment", back_populates="adviser_inputs_build", foreign_keys=[user_build_software_environment_id]
    )

    hardware_information_id = Column(Integer, ForeignKey("hardware_information.id", ondelete="CASCADE"))
    hardware_information = relationship("HardwareInformation", back_populates="adviser_runs")


class Advised(Base, BaseExtension):
    """A relation stating advised software stack."""

    __tablename__ = "advised"

    id = Column(Integer, primary_key=True, autoincrement=True)

    adviser_run_id = Column(Integer, ForeignKey("adviser_run.id", ondelete="CASCADE"))
    python_software_stack_id = Column(Integer, ForeignKey("python_software_stack.id", ondelete="CASCADE"))

    adviser_run = relationship("AdviserRun", back_populates="advised_software_stacks")
    python_software_stack = relationship("PythonSoftwareStack", back_populates="advised_by")


class DependencyMonkeyRun(Base, BaseExtension):
    """A class representing a single dependency-monkey run."""

    __tablename__ = "dependency_monkey_run"

    id = Column(Integer, primary_key=True, autoincrement=True)

    dependency_monkey_document_id = Column(String(256), nullable=False)
    datetime = Column(DateTime, nullable=False)
    dependency_monkey_name = Column(String(256), nullable=False)
    dependency_monkey_version = Column(String(256), nullable=False)
    seed = Column(Integer, nullable=True)
    decision = Column(String(64), nullable=False)
    count = Column(Integer, nullable=True)
    limit_latest_versions = Column(Integer, nullable=True)
    debug = Column(Boolean, default=False)
    dependency_monkey_error = Column(Boolean, default=False)
    duration = Column(Integer, nullable=True)  # XXX: nullable for now

    run_software_environment_id = Column(Integer, ForeignKey("software_environment.id", ondelete="CASCADE"))
    build_software_environment_id = Column(Integer, ForeignKey("software_environment.id", ondelete="CASCADE"))
    run_hardware_information_id = Column(Integer, ForeignKey("hardware_information.id", ondelete="CASCADE"))
    build_hardware_information_id = Column(Integer, ForeignKey("hardware_information.id", ondelete="CASCADE"))

    inspection_runs = relationship("InspectionRun", back_populates="dependency_monkey_run")
    python_package_requirements = relationship(
        "PythonDependencyMonkeyRequirements", back_populates="dependency_monkey_run"
    )
    run_software_environment = relationship(
        "SoftwareEnvironment", back_populates="dependency_monkey_runs_run", foreign_keys=[run_software_environment_id]
    )
    build_software_environment = relationship(
        "SoftwareEnvironment",
        back_populates="dependency_monkey_runs_build",
        foreign_keys=[build_software_environment_id],
    )
    run_hardware_information = relationship(
        "HardwareInformation", back_populates="dependency_monkey_runs_run", foreign_keys=[run_hardware_information_id]
    )
    build_hardware_information = relationship(
        "HardwareInformation",
        back_populates="dependency_monkey_runs_build",
        foreign_keys=[build_hardware_information_id],
    )


class HardwareInformation(Base, BaseExtension):
    """Hardware information base class to derive for specific HW environments."""

    __tablename__ = "hardware_information"

    id = Column(Integer, primary_key=True, autoincrement=True)

    cpu_vendor = Column(Integer, nullable=True)
    cpu_model = Column(Integer, nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    cpu_model_name = Column(String(256), nullable=True)
    cpu_family = Column(Integer, nullable=True)
    cpu_physical_cpus = Column(Integer, nullable=True)

    gpu_model_name = Column(String(256), nullable=True)
    gpu_vendor = Column(String(256), nullable=True)
    gpu_cores = Column(Integer, nullable=True)
    gpu_memory_size = Column(Integer, nullable=True)

    ram_size = Column(Integer, nullable=True)
    is_user = Column(Boolean, nullable=False)

    inspection_runs_run = relationship(
        "InspectionRun",
        back_populates="run_hardware_information",
        foreign_keys="InspectionRun.run_hardware_information_id",
    )
    inspection_runs_build = relationship(
        "InspectionRun",
        back_populates="build_hardware_information",
        foreign_keys="InspectionRun.build_hardware_information_id",
    )
    dependency_monkey_runs_run = relationship(
        "DependencyMonkeyRun",
        back_populates="run_hardware_information",
        foreign_keys="DependencyMonkeyRun.run_hardware_information_id",
    )
    dependency_monkey_runs_build = relationship(
        "DependencyMonkeyRun",
        back_populates="build_hardware_information",
        foreign_keys="DependencyMonkeyRun.build_hardware_information_id",
    )

    adviser_runs = relationship("AdviserRun", back_populates="hardware_information")


class ProvenanceCheckerRun(Base, BaseExtension):
    """A class representing a single provenance-checker run."""

    __tablename__ = "provenance_checker_run"

    id = Column(Integer, primary_key=True, autoincrement=True)

    provenance_checker_document_id = Column(String(256), nullable=False)
    datetime = Column(DateTime, nullable=False)
    provenance_checker_version = Column(String(256), nullable=False)
    provenance_checker_name = Column(String(256), nullable=False)
    origin = Column(String(256), nullable=True)
    debug = Column(Boolean, nullable=False)
    provenance_checker_error = Column(Boolean, nullable=False, default=False)
    # Duration in seconds.
    duration = Column(Integer, nullable=True)  # nullable for now.

    user_software_stack_id = Column(
        Integer, ForeignKey("python_software_stack.id", ondelete="CASCADE"), primary_key=True
    )
    user_software_stack = relationship("PythonSoftwareStack", back_populates="provenance_checker_runs")


class PythonPackageIndex(Base, BaseExtension):
    """Representation of a Python package Index."""

    __tablename__ = "python_package_index"

    id = Column(Integer, primary_key=True, autoincrement=True)

    url = Column(String(256), nullable=False)
    warehouse_api_url = Column(String(256), nullable=True, default=None)
    verify_ssl = Column(Boolean, nullable=False, default=True)
    enabled = Column(Boolean, default=False)

    python_package_versions = relationship("PythonPackageVersion", back_populates="index")
    python_package_requirements = relationship("PythonPackageRequirement", back_populates="index")
    python_package_version_entities = relationship("PythonPackageVersionEntity", back_populates="index")

    __table_args__ = (UniqueConstraint("url"), Index("url_idx", "url", unique=True))


class RPMPackageVersion(Base, BaseExtension):
    """RPM-specific package version."""

    __tablename__ = "rpm_package_version"

    id = Column(Integer, primary_key=True, autoincrement=True)

    package_name = Column(String(256), nullable=False)
    package_version = Column(String(256), nullable=False)
    release = Column(String(256), nullable=True)
    epoch = Column(String(256), nullable=True)
    arch = Column(String(256), nullable=True)
    src = Column(Boolean, nullable=True, default=True)
    package_identifier = Column(String(256), nullable=False)

    rpm_requirements = relationship("RPMRequires", back_populates="rpm_package_version")
    package_extract_runs = relationship("FoundRPM", back_populates="rpm_package_version")


class RPMRequires(Base, BaseExtension):
    """RPM requirement mapping."""

    __tablename__ = "rpm_requires"

    id = Column(Integer, primary_key=True, autoincrement=True)

    rpm_package_version_id = Column(Integer, ForeignKey("rpm_package_version.id", ondelete="CASCADE"), primary_key=True)
    rpm_requirement_id = Column(Integer, ForeignKey("rpm_requirement.id", ondelete="CASCADE"), primary_key=True)

    rpm_package_version = relationship("RPMPackageVersion", back_populates="rpm_requirements")
    rpm_requirement = relationship("RPMRequirement", back_populates="rpm_package_versions")


class RPMRequirement(Base, BaseExtension):
    """Requirement of an RPM as stated in a spec file."""

    __tablename__ = "rpm_requirement"

    id = Column(Integer, primary_key=True, autoincrement=True)

    rpm_requirement_name = Column(String(256), nullable=False)
    rpm_package_versions = relationship("RPMRequires", back_populates="rpm_requirement")


class SoftwareEnvironment(Base, BaseExtension):
    """A base class for environment types."""

    __tablename__ = "software_environment"

    id = Column(Integer, primary_key=True, autoincrement=True)

    environment_name = Column(String(256), nullable=True)
    python_version = Column(String(256), nullable=True)
    image_name = Column(String(256), nullable=True)
    image_sha = Column(String(256), nullable=True)
    os_name = Column(String(256), nullable=True)
    os_version = Column(String(256), nullable=True)
    cuda_version = Column(String(256), nullable=True)
    environment_type = Column(_ENVIRONMENT_TYPE_ENUM, nullable=False)
    is_user = Column(Boolean, default=False, nullable=False)

    adviser_inputs_run = relationship(
        "AdviserRun",
        back_populates="user_run_software_environment",
        foreign_keys="AdviserRun.user_run_software_environment_id",
    )
    adviser_inputs_build = relationship(
        "AdviserRun",
        back_populates="user_build_software_environment",
        foreign_keys="AdviserRun.user_build_software_environment_id",
    )
    dependency_monkey_runs_run = relationship(
        "DependencyMonkeyRun",
        back_populates="build_software_environment",
        foreign_keys="DependencyMonkeyRun.run_software_environment_id",
    )
    dependency_monkey_runs_build = relationship(
        "DependencyMonkeyRun",
        back_populates="build_software_environment",
        foreign_keys="DependencyMonkeyRun.build_software_environment_id",
    )
    inspection_runs_run = relationship(
        "InspectionRun",
        back_populates="build_software_environment",
        foreign_keys="InspectionRun.build_software_environment_id",
    )
    inspection_runs_build = relationship(
        "InspectionRun",
        back_populates="build_software_environment",
        foreign_keys="InspectionRun.run_software_environment_id",
    )
    package_extract_runs = relationship("PackageExtractRun", back_populates="software_environment")
    versioned_symbols = relationship("HasSymbol", back_populates="software_environment")


class IncludedFile(Base, BaseExtension):
    """A relation representing file found in the given artifact."""

    __tablename__ = "included_file"

    id = Column(Integer, primary_key=True, autoincrement=True)

    file = Column(String(256), nullable=False)

    python_file_digest_id = Column(Integer, ForeignKey("python_file_digest.id", ondelete="CASCADE"), primary_key=True)
    python_artifact_id = Column(Integer, ForeignKey("python_artifact.id", ondelete="CASCADE"), primary_key=True)

    python_file_digest = relationship("PythonFileDigest", back_populates="python_artifacts")
    python_artifact = relationship("PythonArtifact", back_populates="python_files")


class Identified(Base, BaseExtension):
    """A relation representing a Python package version identified by a package-extract run."""

    __tablename__ = "identified"

    id = Column(Integer, primary_key=True, autoincrement=True)

    package_extract_run_id = Column(Integer, ForeignKey("package_extract_run.id", ondelete="CASCADE"), primary_key=True)
    python_package_version_id = Column(
        Integer, ForeignKey("python_package_version.id", ondelete="CASCADE"), primary_key=True
    )

    package_extract_run = relationship("PackageExtractRun", back_populates="python_package_version_entities")
    python_package_version = relationship("PythonPackageVersion", back_populates="package_extract_runs")


class HasVulnerability(Base, BaseExtension):
    """The given package version has a vulnerability."""

    __tablename__ = "has_vulnerability"

    id = Column(Integer, primary_key=True, autoincrement=True)

    python_package_version_entity_id = Column(
        Integer, ForeignKey("python_package_version_entity.id", ondelete="CASCADE"), primary_key=True
    )
    cve_id = Column(Integer, ForeignKey("cve.id", ondelete="CASCADE"), primary_key=True)

    python_package_version_entity = relationship("PythonPackageVersionEntity", back_populates="cves")
    cve = relationship("CVE", back_populates="python_package_versions")


class PythonSoftwareStack(Base, BaseExtension):
    """A Python software stack definition."""

    __tablename__ = "python_software_stack"

    id = Column(Integer, primary_key=True, autoincrement=True)

    inspection_runs = relationship("InspectionRun", back_populates="inspection_software_stack")
    adviser_runs = relationship("AdviserRun", back_populates="user_software_stack")
    advised_by = relationship("Advised", back_populates="python_software_stack")
    provenance_checker_runs = relationship("ProvenanceCheckerRun", back_populates="user_software_stack")
    software_stack_type = Column(ENUM("USER", "INSPECTION", "ADVISED", name="software_stack_type", create_type=True))

    performance_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)

    python_package_requirements = relationship("PythonRequirements", back_populates="python_software_stack")
    python_package_versions = relationship("PythonRequirementsLock", back_populates="python_software_stack")


class PythonRequirements(Base, BaseExtension):
    """Requirements for a software stack."""

    __tablename__ = "python_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)

    python_package_requirement_id = Column(
        Integer, ForeignKey("python_package_requirement.id", ondelete="CASCADE"), primary_key=True
    )
    python_software_stack_id = Column(
        Integer, ForeignKey("python_software_stack.id", ondelete="CASCADE"), primary_key=True
    )

    python_package_requirement = relationship("PythonPackageRequirement", back_populates="python_software_stacks")
    python_software_stack = relationship("PythonSoftwareStack", back_populates="python_package_requirements")


class PythonDependencyMonkeyRequirements(Base, BaseExtension):
    """Requirements for a software stack as run on Dependency Monkey."""

    __tablename__ = "python_dependency_monkey_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)

    python_package_requirement_id = Column(
        Integer, ForeignKey("python_package_requirement.id", ondelete="CASCADE"), primary_key=True
    )
    dependency_monkey_run_id = Column(
        Integer, ForeignKey("dependency_monkey_run.id", ondelete="CASCADE"), primary_key=True
    )

    python_package_requirement = relationship("PythonPackageRequirement", back_populates="dependency_monkey_runs")
    dependency_monkey_run = relationship("DependencyMonkeyRun", back_populates="python_package_requirements")


class PythonRequirementsLock(Base, BaseExtension):
    """A pinned down requirements for an application."""

    __tablename__ = "python_requirements_lock"

    id = Column(Integer, primary_key=True, autoincrement=True)

    python_package_version_id = Column(
        Integer, ForeignKey("python_package_version.id", ondelete="CASCADE"), primary_key=True
    )
    python_software_stack_id = Column(
        Integer, ForeignKey("python_software_stack.id", ondelete="CASCADE"), primary_key=True
    )

    python_package_version = relationship("PythonPackageVersion", back_populates="python_software_stacks")
    python_software_stack = relationship("PythonSoftwareStack", back_populates="python_package_versions")


class DebPackageVersion(Base, BaseExtension):
    """Debian-specific package version."""

    __tablename__ = "deb_package_version"

    id = Column(Integer, primary_key=True, autoincrement=True)

    package_name = Column(String(256), nullable=False)
    package_version = Column(String(256), nullable=False)
    epoch = Column(String(256), nullable=True)
    arch = Column(String(256), nullable=True)

    depends = relationship("DebDepends", back_populates="deb_package_version")
    replaces = relationship("DebReplaces", back_populates="deb_package_version")
    pre_depends = relationship("DebPreDepends", back_populates="deb_package_version")
    package_extract_runs = relationship("FoundDeb", back_populates="deb_package_version")


class DebDepends(Base, BaseExtension):
    """Depending relation of a deb package."""

    __tablename__ = "deb_depends"

    id = Column(Integer, primary_key=True, autoincrement=True)

    version_range = Column(String(256), nullable=False)

    deb_dependency_id = Column(Integer, ForeignKey("deb_dependency.id", ondelete="CASCADE"), primary_key=True)
    deb_package_version_id = Column(Integer, ForeignKey("deb_package_version.id", ondelete="CASCADE"), primary_key=True)

    deb_package_version = relationship("DebPackageVersion", back_populates="depends")
    deb_dependency = relationship("DebDependency", back_populates="deb_package_versions_depends")


class DebPreDepends(Base, BaseExtension):
    """Pre-depending relation of a deb package."""

    __tablename__ = "deb_pre_depends"

    id = Column(Integer, primary_key=True, autoincrement=True)

    deb_dependency_id = Column(Integer, ForeignKey("deb_dependency.id", ondelete="CASCADE"), primary_key=True)
    deb_package_version_id = Column(Integer, ForeignKey("deb_package_version.id", ondelete="CASCADE"), primary_key=True)

    version_range = Column(String(256), nullable=True)
    deb_package_version = relationship("DebPackageVersion", back_populates="pre_depends")
    deb_dependency = relationship("DebDependency", back_populates="deb_package_versions_pre_depends")


class DebReplaces(Base, BaseExtension):
    """A relation of a deb package capturing package replacement.."""

    __tablename__ = "deb_replaces"

    id = Column(Integer, primary_key=True, autoincrement=True)

    deb_dependency_id = Column(Integer, ForeignKey("deb_dependency.id", ondelete="CASCADE"), primary_key=True)
    deb_package_version_id = Column(Integer, ForeignKey("deb_package_version.id", ondelete="CASCADE"), primary_key=True)

    version_range = Column(String(256), nullable=False)
    deb_package_version = relationship("DebPackageVersion", back_populates="replaces")
    deb_dependency = relationship("DebDependency", back_populates="deb_package_versions_replaces")


class DebDependency(Base, BaseExtension):
    """A Debian dependency."""

    __tablename__ = "deb_dependency"

    id = Column(Integer, primary_key=True, autoincrement=True)

    package_name = Column(String(256), nullable=False)

    deb_package_versions_depends = relationship("DebDepends", back_populates="deb_dependency")
    deb_package_versions_pre_depends = relationship("DebPreDepends", back_populates="deb_dependency")
    deb_package_versions_replaces = relationship("DebReplaces", back_populates="deb_dependency")


class VersionedSymbol(Base, BaseExtension):
    """A system symbol."""

    __tablename__ = "versioned_symbol"

    id = Column(Integer, primary_key=True, autoincrement=True)

    library_name = Column(String(256), nullable=False)
    symbol = Column(String(256), nullable=False)

    package_extract_runs = relationship("DetectedSymbol", back_populates="versioned_symbol")
    software_environments = relationship("HasSymbol", back_populates="versioned_symbol")
    python_artifacts = relationship("RequiresSymbol", back_populates="versioned_symbol")


class HasSymbol(Base, BaseExtension):
    """A relation stating a software environment has a symbol."""

    __tablename__ = "has_symbol"

    id = Column(Integer, primary_key=True, autoincrement=True)

    software_environment_id = Column(
        Integer, ForeignKey("software_environment.id", ondelete="CASCADE"), primary_key=True
    )
    versioned_symbol_id = Column(Integer, ForeignKey("versioned_symbol.id", ondelete="CASCADE"), primary_key=True)

    software_environment = relationship("SoftwareEnvironment", back_populates="versioned_symbols")
    versioned_symbol = relationship("VersionedSymbol", back_populates="software_environments")


class RequiresSymbol(Base, BaseExtension):
    """A relation stating a software environment has a symbol."""

    __tablename__ = "requires_symbol"

    id = Column(Integer, primary_key=True, autoincrement=True)

    python_artifact_id = Column(Integer, ForeignKey("python_artifact.id", ondelete="CASCADE"), primary_key=True)
    versioned_symbol_id = Column(Integer, ForeignKey("versioned_symbol.id", ondelete="CASCADE"), primary_key=True)

    python_artifact = relationship("PythonArtifact", back_populates="versioned_symbols")
    versioned_symbol = relationship("VersionedSymbol", back_populates="python_artifacts")


class DetectedSymbol(Base, BaseExtension):
    """A relation stating a package extract run detected a symbol."""

    __tablename__ = "detected_symbol"

    id = Column(Integer, primary_key=True, autoincrement=True)

    package_extract_run_id = Column(Integer, ForeignKey("package_extract_run.id", ondelete="CASCADE"), primary_key=True)
    versioned_symbol_id = Column(Integer, ForeignKey("versioned_symbol.id", ondelete="CASCADE"), primary_key=True)

    package_extract_run = relationship("PackageExtractRun", back_populates="versioned_symbols")
    versioned_symbol = relationship("VersionedSymbol", back_populates="package_extract_runs")
