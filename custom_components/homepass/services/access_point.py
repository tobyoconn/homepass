"""Application-facing Access Point definitions and name-independent targets."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final, Protocol
from uuid import UUID, uuid4

from ..exceptions import AccessPointHasGrantsError
from ..models import AccessDriver, AccessPoint, ActivityEventType
from .activity_producer import ActivityProducer

_LOGGER = logging.getLogger(__name__)
_BUILT_IN_TIMESTAMP: Final = datetime(2026, 7, 15, tzinfo=UTC)

type AccessPointChangeListener = Callable[[], Awaitable[None]]
type AccessPointRemoveHook = Callable[[UUID], Awaitable[object]]

FRONT_DOOR_ACCESS_POINT: Final = AccessPoint(
    id=UUID("00000000-0000-4000-8000-000000000001"),
    display_name="Lock",
    enabled=True,
    created_at=_BUILT_IN_TIMESTAMP,
    updated_at=_BUILT_IN_TIMESTAMP,
)
BUILT_IN_ACCESS_POINTS: Final[tuple[AccessPoint, ...]] = (FRONT_DOOR_ACCESS_POINT,)


@dataclass(frozen=True, slots=True)
class AccessPointTarget:
    """Application-facing binding for a physical Home Assistant target."""

    access_point: AccessPoint
    lock_entity_id: str
    driver: AccessDriver | None = AccessDriver.ZWAVE_JS
    home_assistant_instance: str = "local"
    display_name_override: str | None = None
    migrate_generated_display_name: bool = False
    discovery_key: str | None = None
    control_profile: str = "lock"
    status_entity_id: str | None = None
    status_inverted: bool = False
    pulse_seconds: float = 1.0
    pin_capable: bool = True
    nfc_capable: bool = True
    device_id: str | None = None

    @property
    def control_entity_id(self) -> str:
        """Return the control entity while retaining the legacy field name."""
        return self.lock_entity_id


@dataclass(frozen=True, slots=True)
class AccessPointEnrollment:
    """Persisted opt-in relationship for one managed Access Point."""

    access_point_id: UUID
    discovery_key: str | None
    managed: bool = True
    control_entity_id: str | None = None
    status_entity_id: str | None = None
    control_profile: str = "lock"
    status_inverted: bool = False
    pulse_seconds: float = 1.0
    pin_capable: bool = True
    nfc_capable: bool = True
    device_id: str | None = None


class AccessPointAvailability(StrEnum):
    """Sanitized availability reported for an Access Point target."""

    AVAILABLE = "available"
    OFFLINE = "offline"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AccessPointState:
    """Current Home Assistant state and local live-update sources for one Access Point."""

    availability: AccessPointAvailability
    lock_state: str | None = None
    door_state: str | None = None
    last_updated: datetime | None = None
    lock_entity_id: str | None = None
    door_entity_id: str | None = None
    battery_percentage: int | None = None
    battery_status: str | None = None
    battery_entity_id: str | None = None
    door_sensor_battery_percentage: int | None = None
    door_sensor_battery_status: str | None = None
    door_sensor_battery_entity_id: str | None = None
    supports_open: bool = False
    recommended_entry_action: str | None = None


@dataclass(frozen=True, slots=True)
class AccessPointSummary:
    """Frontend-safe Access Point identity and current operational state."""

    access_point: AccessPoint
    state: AccessPointState
    control_profile: str = "lock"
    pin_capable: bool = True
    nfc_capable: bool = True
    status_inverted: bool = False
    status_editable: bool = False

    def to_dict(self) -> dict[str, object]:
        """Serialize without exposing Home Assistant or driver identifiers."""
        data: dict[str, object] = dict(self.access_point.to_dict())
        data["availability"] = self.state.availability.value
        if self.state.lock_state is not None:
            data["lock_state"] = self.state.lock_state
        if self.state.door_state is not None:
            data["door_state"] = self.state.door_state
        if self.state.last_updated is not None:
            data["last_updated"] = self.state.last_updated.isoformat()
        if self.state.lock_entity_id is not None:
            data["lock_entity_id"] = self.state.lock_entity_id
        if self.state.door_entity_id is not None:
            data["door_entity_id"] = self.state.door_entity_id
        if self.state.battery_status is not None:
            data["battery_status"] = self.state.battery_status
        if self.state.battery_percentage is not None:
            data["battery_percentage"] = self.state.battery_percentage
        if self.state.battery_entity_id is not None:
            data["battery_entity_id"] = self.state.battery_entity_id
        if self.state.door_sensor_battery_status is not None:
            data["door_sensor_battery_status"] = self.state.door_sensor_battery_status
        if self.state.door_sensor_battery_percentage is not None:
            data["door_sensor_battery_percentage"] = self.state.door_sensor_battery_percentage
        if self.state.door_sensor_battery_entity_id is not None:
            data["door_sensor_battery_entity_id"] = self.state.door_sensor_battery_entity_id
        data["supports_open"] = self.state.supports_open
        data["recommended_entry_action"] = self.state.recommended_entry_action
        data["control_profile"] = self.control_profile
        data["capabilities"] = {
            "app": True,
            "pin": self.pin_capable,
            "nfc": self.nfc_capable,
            "lock": self.control_profile == "lock",
            "cover": self.control_profile == "garage_cover",
            "relay": self.control_profile in {"garage_toggle", "electric_strike"},
            "status": self.state.door_entity_id is not None,
            "status_editable": self.status_editable,
        }
        data["status_inverted"] = self.status_inverted
        return data


class AccessPointNameResolver(Protocol):
    """Resolve a Home Assistant-owned display name for one lock entity."""

    async def resolve_name(self, lock_entity_id: str) -> str:
        """Return the best available Home Assistant display name."""


class AccessPointStateResolver(Protocol):
    """Resolve frontend-safe current state for one Access Point target."""

    async def resolve_state(self, target: AccessPointTarget) -> AccessPointState:
        """Return truthful current state without exposing target identifiers."""


class AccessPointTargetDiscovery(Protocol):
    """Discover the currently supported Home Assistant Access Point targets."""

    async def discover_targets(self) -> tuple[AccessPointTarget, ...]:
        """Return enabled supported targets in deterministic order."""


class AccessPointEnrollmentStore(Protocol):
    """Persist explicitly managed Access Point identities."""

    async def list_all(self) -> tuple[AccessPointEnrollment, ...]: ...

    async def upsert(
        self,
        enrollment: AccessPointEnrollment,
        access_point: AccessPoint,
        *,
        expected_policy_updated_at: datetime | None = None,
        clear_name_fallback: bool = False,
    ) -> AccessPointEnrollment: ...

    async def remove(self, access_point_id: UUID) -> None: ...


class AccessPointPolicyStore(Protocol):
    """Persist and load stable Access Point policy definitions."""

    async def get(self, access_point_id: UUID) -> AccessPoint: ...

    async def list_all(self) -> tuple[AccessPoint, ...]: ...

    async def list_name_fallback_ids(self) -> frozenset[UUID]: ...

    async def update(
        self,
        access_point: AccessPoint,
        *,
        expected_updated_at: datetime,
    ) -> AccessPoint: ...


class AccessPointGrantLookup(Protocol):
    """Report whether an Access Point remains referenced by a grant."""

    async def has_for_access_point(self, access_point_id: UUID) -> bool: ...


FRONT_DOOR_TARGET: Final = AccessPointTarget(
    access_point=FRONT_DOOR_ACCESS_POINT,
    lock_entity_id="lock.example_front_door_lock",
    migrate_generated_display_name=True,
)
BUILT_IN_ACCESS_POINT_TARGETS: Final[tuple[AccessPointTarget, ...]] = (FRONT_DOOR_TARGET,)


class AccessPointService:
    """Expose available Access Points to application consumers."""

    def __init__(
        self,
        targets: tuple[AccessPointTarget, ...] = BUILT_IN_ACCESS_POINT_TARGETS,
        name_resolver: AccessPointNameResolver | None = None,
        state_resolver: AccessPointStateResolver | None = None,
        target_discovery: AccessPointTargetDiscovery | None = None,
        enrollment_store: AccessPointEnrollmentStore | None = None,
        policy_store: AccessPointPolicyStore | None = None,
        grant_lookup: AccessPointGrantLookup | None = None,
        activity_producer: ActivityProducer | None = None,
        before_remove: AccessPointRemoveHook | None = None,
    ) -> None:
        """Initialize with configured application-facing targets."""
        self._targets = targets
        self._name_resolver = name_resolver
        self._state_resolver = state_resolver
        self._target_discovery = target_discovery
        self._enrollment_store = enrollment_store
        self._policy_store = policy_store
        self._grant_lookup = grant_lookup
        self._activity_producer = activity_producer
        self._before_remove = before_remove
        self._change_listeners: list[AccessPointChangeListener] = []

    def add_change_listener(self, listener: AccessPointChangeListener) -> Callable[[], None]:
        """Observe completed policy/enrollment changes without coupling operations."""
        if listener not in self._change_listeners:
            self._change_listeners.append(listener)

        def remove_listener() -> None:
            if listener in self._change_listeners:
                self._change_listeners.remove(listener)

        return remove_listener

    async def list_access_points(self) -> tuple[AccessPoint, ...]:
        """Return managed policy definitions without requiring live discovery."""
        if self._policy_store is not None and self._enrollment_store is not None:
            managed_ids = {
                enrollment.access_point_id
                for enrollment in await self._enrollments()
                if enrollment.managed
            }
            return tuple(
                access_point
                for access_point in await self._policy_store.list_all()
                if access_point.id in managed_ids and access_point.enabled
            )
        access_points: list[AccessPoint] = []
        for target in await self._current_targets():
            if target.access_point.enabled:
                access_points.append((await self._resolved_target(target)).access_point)
        return tuple(access_points)

    async def get_target(self, access_point_id: UUID) -> AccessPointTarget:
        """Return the currently discovered target for an Access Point identifier."""
        for target in await self._current_targets():
            if target.access_point.id == access_point_id and target.access_point.enabled:
                return await self._resolved_target(target)
        raise ValueError("Access point is not available")

    async def get_access_point(self, access_point_id: UUID) -> AccessPoint:
        """Return the durable Access Point policy without requiring discovery."""
        if self._policy_store is not None:
            return await self._policy_store.get(access_point_id)
        return (await self.get_target(access_point_id)).access_point

    async def resolve_state(self, access_point_id: UUID) -> AccessPointState:
        """Return current normalized operational state for command safety checks."""
        target = await self.get_target(access_point_id)
        if self._state_resolver is None:
            return AccessPointState(AccessPointAvailability.UNKNOWN)
        return await self._state_resolver.resolve_state(target)

    async def list_access_point_summaries(self) -> tuple[AccessPointSummary, ...]:
        """Return enabled Access Points with sanitized current Home Assistant state."""
        summaries: list[AccessPointSummary] = []
        for target in await self._current_targets():
            if not target.access_point.enabled:
                continue
            resolved = await self._resolved_target(target)
            state = (
                await self._state_resolver.resolve_state(resolved)
                if self._state_resolver is not None
                else AccessPointState(AccessPointAvailability.UNKNOWN)
            )
            summaries.append(
                AccessPointSummary(
                    resolved.access_point,
                    state,
                    control_profile=resolved.control_profile,
                    pin_capable=resolved.pin_capable,
                    nfc_capable=resolved.nfc_capable,
                    status_inverted=resolved.status_inverted,
                    status_editable=resolved.device_id is not None,
                )
            )
        if self._policy_store is not None and self._enrollment_store is not None:
            enrollments_by_id = {
                enrollment.access_point_id: enrollment
                for enrollment in await self._enrollments()
                if enrollment.managed
            }
            discovered_ids = {summary.access_point.id for summary in summaries}
            managed_ids = set(enrollments_by_id)
            summaries.extend(
                AccessPointSummary(
                    access_point,
                    AccessPointState(AccessPointAvailability.OFFLINE),
                    control_profile=enrollments_by_id[access_point.id].control_profile,
                    pin_capable=enrollments_by_id[access_point.id].pin_capable,
                    nfc_capable=enrollments_by_id[access_point.id].nfc_capable,
                    status_inverted=enrollments_by_id[access_point.id].status_inverted,
                    status_editable=(enrollments_by_id[access_point.id].device_id is not None),
                )
                for access_point in await self._policy_store.list_all()
                if access_point.enabled
                and access_point.id in managed_ids
                and access_point.id not in discovered_ids
            )
        return tuple(
            sorted(
                summaries,
                key=lambda summary: (
                    summary.access_point.display_name.casefold(),
                    str(summary.access_point.id),
                ),
            )
        )

    async def list_available_access_point_summaries(self) -> tuple[AccessPointSummary, ...]:
        """Return compatible discovered locks that are not managed by HomePASS."""
        managed = await self._enrollments()
        targets = await self._discovered_targets()
        available = [
            self._restore_known_identity(target, managed)
            for target in targets
            if not self._is_enrolled(target, managed)
        ]
        return await self._summaries(tuple(available))

    async def enroll_access_point(
        self,
        access_point_id: UUID,
        *,
        open_enabled: bool | None = None,
        entry_action: str = "unlock",
    ) -> AccessPointSummary:
        """Persist one currently compatible discovered lock as managed."""
        operation_id = uuid4()
        targets = await self._discovered_targets()
        enrollments = await self._enrollments()
        existing = next(
            (item for item in enrollments if item.access_point_id == access_point_id), None
        )
        target = next(
            (
                item
                for item in targets
                if item.access_point.id == access_point_id
                or (existing is not None and item.discovery_key == existing.discovery_key)
            ),
            None,
        )
        if target is None:
            raise ValueError("This available lock is no longer available")
        if self._enrollment_store is None:
            raise ValueError("Access Point enrolment is unavailable")
        configured = next(
            (item for item in self._targets if item.lock_entity_id == target.lock_entity_id),
            None,
        )
        if configured is not None:
            target = replace(configured, discovery_key=target.discovery_key)
        enrollment = AccessPointEnrollment(
            existing.access_point_id if existing is not None else target.access_point.id,
            target.discovery_key,
        )
        resolved = await self._resolved_target(target)
        if resolved.access_point.id != enrollment.access_point_id:
            resolved = replace(
                resolved,
                access_point=replace(resolved.access_point, id=enrollment.access_point_id),
            )
        policy = resolved.access_point
        expected_policy_updated_at: datetime | None = None
        clear_name_fallback = False
        if existing is not None and self._policy_store is not None:
            retained = await self._policy_store.get(enrollment.access_point_id)
            expected_policy_updated_at = retained.updated_at
            fallback_ids = await self._policy_store.list_name_fallback_ids()
            if (
                retained.id in fallback_ids
                and retained.display_name != resolved.access_point.display_name
            ):
                policy = replace(
                    retained,
                    display_name=resolved.access_point.display_name,
                    updated_at=max(datetime.now(UTC), retained.updated_at),
                )
                clear_name_fallback = True
            else:
                policy = retained
            resolved = replace(resolved, access_point=policy)
        state = await self._state_resolver.resolve_state(resolved) if self._state_resolver else None
        self._validate_open_policy(state, open_enabled, entry_action, onboarding=True)
        policy = replace(policy, open_enabled=bool(open_enabled), entry_action=entry_action)
        resolved = replace(resolved, access_point=policy)
        await self._enrollment_store.upsert(
            enrollment,
            policy,
            expected_policy_updated_at=expected_policy_updated_at,
            clear_name_fallback=clear_name_fallback,
        )
        summary = await self._summary(resolved)
        if (existing is None or not existing.managed) and self._activity_producer is not None:
            await self._activity_producer.record(
                ActivityEventType.DOOR_ADDED,
                occurred_at=datetime.now(UTC),
                source_event_key=f"access-point-enrollment:{operation_id}:added",
                access_point=summary.access_point,
                correlation_id=operation_id,
            )
        await self._notify_change_listeners()
        return summary

    async def enroll_home_assistant_access_point(
        self,
        *,
        display_name: str,
        control_entity_id: str,
        control_profile: str,
        status_entity_id: str | None = None,
        device_id: str | None = None,
        status_inverted: bool = False,
        pulse_seconds: float = 1.0,
        open_enabled: bool | None = None,
        entry_action: str = "unlock",
    ) -> AccessPointSummary:
        """Persist an administrator-selected Home Assistant device binding."""
        if self._enrollment_store is None or self._policy_store is None:
            raise ValueError("Access Point enrolment is unavailable")
        display_name = display_name.strip()
        control_entity_id = control_entity_id.strip()
        status_entity_id = status_entity_id.strip() if status_entity_id else None
        device_id = device_id.strip() if device_id else None
        if not display_name:
            raise ValueError("Door name is required")
        if "." not in control_entity_id:
            raise ValueError("A valid Home Assistant control entity is required")
        allowed_profiles = {"lock", "garage_cover", "garage_toggle", "electric_strike"}
        if control_profile not in allowed_profiles:
            raise ValueError("Unsupported Home Assistant door type")
        if isinstance(pulse_seconds, bool) or not 0.1 <= float(pulse_seconds) <= 10:
            raise ValueError("Relay pulse must be between 0.1 and 10 seconds")

        enrollments = await self._enrollments()
        duplicate = next(
            (
                item
                for item in enrollments
                if item.managed and item.control_entity_id == control_entity_id
            ),
            None,
        )
        if duplicate is not None:
            raise ValueError("This Home Assistant entity is already managed by HomePASS")
        known = next(
            (item for item in enrollments if item.control_entity_id == control_entity_id),
            None,
        )
        now = datetime.now(UTC)
        access_point_id = known.access_point_id if known is not None else uuid4()
        retained = await self._policy_store.get(access_point_id) if known is not None else None
        policy = (
            AccessPoint(
                id=access_point_id,
                display_name=display_name,
                created_at=now,
                updated_at=now,
            )
            if retained is None
            else replace(
                retained,
                display_name=display_name,
                enabled=True,
                updated_at=max(now, retained.updated_at),
            )
        )
        enrollment = AccessPointEnrollment(
            access_point_id=access_point_id,
            discovery_key=f"manual:{control_entity_id}",
            managed=True,
            control_entity_id=control_entity_id,
            status_entity_id=status_entity_id,
            control_profile=control_profile,
            status_inverted=status_inverted,
            pulse_seconds=float(pulse_seconds),
            pin_capable=False,
            nfc_capable=(control_profile != "garage_toggle" or status_entity_id is not None),
            device_id=device_id,
        )
        target = self._target_from_enrollment(enrollment, policy)
        state = await self._state_resolver.resolve_state(target) if self._state_resolver else None
        self._validate_open_policy(state, open_enabled, entry_action, onboarding=True)
        policy = replace(policy, open_enabled=bool(open_enabled), entry_action=entry_action)
        target = replace(target, access_point=policy)
        await self._enrollment_store.upsert(
            enrollment,
            policy,
            expected_policy_updated_at=retained.updated_at if retained is not None else None,
        )
        summary = await self._summary(target)
        if self._activity_producer is not None:
            operation_id = uuid4()
            await self._activity_producer.record(
                ActivityEventType.DOOR_ADDED,
                occurred_at=now,
                source_event_key=f"access-point-enrollment:{operation_id}:added",
                access_point=policy,
                correlation_id=operation_id,
            )
        await self._notify_change_listeners()
        return summary

    async def update_access_point_policy(
        self,
        access_point_id: UUID,
        *,
        display_name: str | None = None,
        enabled: bool | None = None,
    ) -> AccessPoint:
        """Update durable homeowner policy without consulting live discovery."""
        if self._policy_store is None:
            raise ValueError("Access Point policy persistence is unavailable")
        current = await self._policy_store.get(access_point_id)
        if display_name is not None:
            display_name = display_name.strip()
            if not display_name:
                raise ValueError("Door name is required")
            if len(display_name) > 80:
                raise ValueError("Door name must be 80 characters or fewer")
        next_display_name = current.display_name if display_name is None else display_name
        next_enabled = current.enabled if enabled is None else enabled
        assignment_requested = display_name is not None or enabled is not None
        if not assignment_requested:
            return current
        name_changed = next_display_name != current.display_name
        enabled_changed = next_enabled != current.enabled
        updated = replace(
            current,
            display_name=next_display_name,
            enabled=next_enabled,
            updated_at=max(datetime.now(UTC), current.updated_at),
        )
        saved = await self._policy_store.update(
            updated,
            expected_updated_at=current.updated_at,
        )
        if self._activity_producer is not None:
            correlation_id = uuid4()
            if name_changed:
                await self._activity_producer.record(
                    ActivityEventType.DOOR_UPDATED,
                    occurred_at=saved.updated_at,
                    source_event_key=(
                        f"access-point:{access_point_id}:renamed:{saved.updated_at.isoformat()}"
                    ),
                    access_point=saved,
                    correlation_id=correlation_id,
                )
            if enabled_changed:
                await self._activity_producer.record(
                    (
                        ActivityEventType.DOOR_ENABLED
                        if saved.enabled
                        else ActivityEventType.DOOR_DISABLED
                    ),
                    occurred_at=saved.updated_at,
                    source_event_key=(
                        f"access-point:{access_point_id}:enabled:{saved.updated_at.isoformat()}"
                    ),
                    access_point=saved,
                    correlation_id=correlation_id,
                )
        if name_changed or enabled_changed:
            await self._notify_change_listeners()
        return saved

    @staticmethod
    def _validate_open_policy(
        state: AccessPointState | None,
        open_enabled: bool | None,
        entry_action: str,
        *,
        onboarding: bool = False,
    ) -> None:
        supports_open = state is not None and state.supports_open is True
        if onboarding and supports_open and open_enabled is None:
            raise ValueError("Confirm whether HomePASS should enable Open Door")
        if open_enabled is not None and not isinstance(open_enabled, bool):
            raise ValueError("Open permission must be a boolean")
        if open_enabled and not supports_open:
            raise ValueError("This lock does not currently support Open Door")
        if entry_action not in {"unlock", "open"} or (entry_action == "open" and not open_enabled):
            raise ValueError("Open Door must be enabled before using it for entry")

    async def update_open_policy(
        self,
        access_point_id: UUID,
        *,
        open_enabled: bool,
        entry_action: str,
    ) -> AccessPointSummary:
        """Persist administrator-confirmed entry policy without changing Nuki settings."""
        if self._policy_store is None:
            raise ValueError("Access Point policy persistence is unavailable")
        target = await self.get_target(access_point_id)
        state = await self.resolve_state(access_point_id)
        self._validate_open_policy(state, open_enabled, entry_action)
        current = await self._policy_store.get(access_point_id)
        updated = replace(
            current,
            open_enabled=open_enabled,
            entry_action=entry_action,
            updated_at=max(datetime.now(UTC), current.updated_at),
        )
        await self._policy_store.update(updated, expected_updated_at=current.updated_at)
        await self._notify_change_listeners()
        return await self._summary(replace(target, access_point=updated))

    async def update_access_point_status(
        self,
        access_point_id: UUID,
        *,
        status_entity_id: str | None,
        status_inverted: bool,
    ) -> AccessPointSummary:
        """Update a manually bound Door's separate open/closed status source."""
        if self._enrollment_store is None or self._policy_store is None:
            raise ValueError("Access Point enrolment is unavailable")
        status_entity_id = status_entity_id.strip() if status_entity_id else None
        if status_entity_id is not None and "." not in status_entity_id:
            raise ValueError("A valid Home Assistant status entity is required")
        enrollment = next(
            (
                item
                for item in await self._enrollment_store.list_all()
                if item.access_point_id == access_point_id and item.managed
            ),
            None,
        )
        if enrollment is None:
            raise ValueError("Door is not managed by HomePASS")
        if enrollment.control_entity_id is None:
            raise ValueError(
                "This automatically discovered Door already manages its own status source"
            )
        if status_entity_id == enrollment.control_entity_id:
            raise ValueError("Control and status entities must be different")
        if enrollment.control_profile == "garage_toggle" and status_entity_id is None:
            raise ValueError("A pulse/toggle Door requires an open/closed status entity")
        if (
            enrollment.status_entity_id == status_entity_id
            and enrollment.status_inverted is status_inverted
        ):
            return await self._summary(
                self._target_from_enrollment(
                    enrollment,
                    await self._policy_store.get(access_point_id),
                )
            )
        policy = await self._policy_store.get(access_point_id)
        updated = replace(
            enrollment,
            status_entity_id=status_entity_id,
            status_inverted=status_inverted,
            nfc_capable=(
                enrollment.control_profile != "garage_toggle" or status_entity_id is not None
            ),
        )
        await self._enrollment_store.upsert(
            updated,
            policy,
            expected_policy_updated_at=policy.updated_at,
        )
        await self._notify_change_listeners()
        return await self._summary(self._target_from_enrollment(updated, policy))

    async def set_keypad_pin_capable(
        self,
        access_point_id: UUID,
        *,
        enabled: bool,
    ) -> None:
        """Expose PIN access when a HomePASS keypad is associated with a Door."""
        if self._enrollment_store is None or self._policy_store is None:
            raise ValueError("Access Point enrolment is unavailable")
        enrollment = next(
            (
                item
                for item in await self._enrollment_store.list_all()
                if item.access_point_id == access_point_id and item.managed
            ),
            None,
        )
        if enrollment is None:
            raise ValueError("Door is not managed by HomePASS")
        if enrollment.control_profile == "lock" or enrollment.pin_capable is enabled:
            return
        if (
            not enabled
            and self._grant_lookup is not None
            and await self._grant_lookup.has_for_access_point(access_point_id)
        ):
            raise ValueError("Remove User PIN access from this Door before removing its keypad")
        policy = await self._policy_store.get(access_point_id)
        await self._enrollment_store.upsert(
            replace(enrollment, pin_capable=enabled),
            policy,
            expected_policy_updated_at=policy.updated_at,
        )
        await self._notify_change_listeners()

    async def remove_access_point(self, access_point_id: UUID) -> None:
        """Remove only HomePASS enrolment after proving no grants remain."""
        enrollment = next(
            (item for item in await self._enrollments() if item.access_point_id == access_point_id),
            None,
        )
        access_point = (
            await self.get_access_point(access_point_id)
            if enrollment is not None and enrollment.managed
            else None
        )
        if self._grant_lookup is not None and await self._grant_lookup.has_for_access_point(
            access_point_id
        ):
            raise AccessPointHasGrantsError("This door still has access assigned")
        if self._before_remove is not None:
            await self._before_remove(access_point_id)
        if self._enrollment_store is not None:
            await self._enrollment_store.remove(access_point_id)
        if access_point is not None and self._activity_producer is not None:
            operation_id = uuid4()
            await self._activity_producer.record(
                ActivityEventType.DOOR_REMOVED,
                occurred_at=datetime.now(UTC),
                source_event_key=f"access-point-enrollment:{operation_id}:removed",
                access_point=access_point,
                correlation_id=operation_id,
            )
        await self._notify_change_listeners()

    async def _notify_change_listeners(self) -> None:
        for listener in tuple(self._change_listeners):
            try:
                await listener()
            except Exception:  # noqa: BLE001 - observers cannot fail the completed operation
                _LOGGER.warning("An Access Point change observer failed")

    async def _current_targets(self) -> tuple[AccessPointTarget, ...]:
        """Reconcile configured identities with current discovery results."""
        if self._target_discovery is None or self._enrollment_store is None:
            return self._targets
        managed = await self._enrollments()
        policies = (
            {item.id: item for item in await self._policy_store.list_all()}
            if self._policy_store is not None
            else {}
        )
        name_fallback_ids = (
            await self._policy_store.list_name_fallback_ids()
            if self._policy_store is not None
            else frozenset()
        )
        discovered_targets = await self._discovered_targets()
        discovered_by_entity = {target.lock_entity_id: target for target in discovered_targets}
        configured_by_entity = {target.lock_entity_id: target for target in self._targets}
        reconciled: list[AccessPointTarget] = []
        seen_ids: set[UUID] = set()
        seen_entities: set[str] = set()
        for enrollment in managed:
            if (
                not enrollment.managed
                or enrollment.control_entity_id is None
                or enrollment.access_point_id not in policies
            ):
                continue
            target = self._target_from_enrollment(enrollment, policies[enrollment.access_point_id])
            discovered = discovered_by_entity.get(enrollment.control_entity_id)
            if discovered is not None:
                target = replace(
                    target,
                    driver=discovered.driver,
                    pin_capable=discovered.pin_capable,
                )
            if not target.access_point.enabled:
                continue
            reconciled.append(target)
            seen_ids.add(target.access_point.id)
            seen_entities.add(target.control_entity_id)
        for discovered in discovered_targets:
            enrollment = next(
                (
                    item
                    for item in managed
                    if item.access_point_id == discovered.access_point.id
                    or item.discovery_key == discovered.discovery_key
                ),
                None,
            )
            if enrollment is None or not enrollment.managed:
                continue
            if enrollment.control_entity_id is not None:
                continue
            configured = configured_by_entity.get(discovered.lock_entity_id)
            target = (
                replace(configured, discovery_key=discovered.discovery_key)
                if configured is not None
                else replace(
                    discovered,
                    access_point=replace(discovered.access_point, id=enrollment.access_point_id),
                )
            )
            policy = policies.get(enrollment.access_point_id)
            expected_policy_updated_at = policy.updated_at if policy is not None else None
            clear_name_fallback = False
            if policy is not None:
                target = replace(
                    target,
                    access_point=policy,
                    display_name_override=None,
                    migrate_generated_display_name=policy.id in name_fallback_ids,
                )
            target = await self._resolved_target(target)
            policy_changed = False
            if (
                policy is not None
                and policy.id in name_fallback_ids
                and target.access_point.display_name != policy.display_name
            ):
                policy = replace(
                    policy,
                    display_name=target.access_point.display_name,
                    updated_at=max(datetime.now(UTC), policy.updated_at),
                )
                target = replace(target, access_point=policy)
                policy_changed = True
                clear_name_fallback = True
            discovery_key_changed = (
                enrollment.discovery_key is None and target.discovery_key is not None
            )
            if discovery_key_changed or policy_changed:
                await self._enrollment_store.upsert(
                    replace(enrollment, discovery_key=target.discovery_key),
                    target.access_point,
                    expected_policy_updated_at=expected_policy_updated_at,
                    clear_name_fallback=clear_name_fallback,
                )
            if (
                target.access_point.id in seen_ids
                or target.lock_entity_id in seen_entities
                or not target.access_point.enabled
            ):
                continue
            seen_ids.add(target.access_point.id)
            seen_entities.add(target.lock_entity_id)
            reconciled.append(target)
        return tuple(reconciled)

    @staticmethod
    def _target_from_enrollment(
        enrollment: AccessPointEnrollment, policy: AccessPoint
    ) -> AccessPointTarget:
        """Build a live target from one administrator-managed HA binding."""
        if enrollment.control_entity_id is None:
            raise ValueError("Home Assistant control entity is unavailable")
        return AccessPointTarget(
            access_point=policy,
            lock_entity_id=enrollment.control_entity_id,
            discovery_key=enrollment.discovery_key,
            control_profile=enrollment.control_profile,
            status_entity_id=enrollment.status_entity_id,
            status_inverted=enrollment.status_inverted,
            pulse_seconds=enrollment.pulse_seconds,
            pin_capable=enrollment.pin_capable,
            nfc_capable=enrollment.nfc_capable,
            device_id=enrollment.device_id,
            driver=(
                AccessDriver.ZWAVE_JS
                if enrollment.pin_capable and enrollment.control_profile == "lock"
                else AccessDriver.HOMEPASS_KEYPAD
                if enrollment.pin_capable
                else None
            ),
        )

    async def _discovered_targets(self) -> tuple[AccessPointTarget, ...]:
        if self._target_discovery is None:
            return self._targets
        return await self._target_discovery.discover_targets()

    async def _enrollments(self) -> tuple[AccessPointEnrollment, ...]:
        if self._enrollment_store is None:
            return tuple(
                AccessPointEnrollment(target.access_point.id, target.discovery_key)
                for target in self._targets
            )
        return await self._enrollment_store.list_all()

    @staticmethod
    def _is_enrolled(
        target: AccessPointTarget, enrollments: tuple[AccessPointEnrollment, ...]
    ) -> bool:
        return any(
            item.managed
            and (
                item.access_point_id == target.access_point.id
                or (item.discovery_key is not None and item.discovery_key == target.discovery_key)
            )
            for item in enrollments
        )

    @staticmethod
    def _restore_known_identity(
        target: AccessPointTarget, enrollments: tuple[AccessPointEnrollment, ...]
    ) -> AccessPointTarget:
        known = next(
            (
                item
                for item in enrollments
                if item.discovery_key is not None and item.discovery_key == target.discovery_key
            ),
            None,
        )
        return (
            target
            if known is None
            else replace(
                target,
                access_point=replace(target.access_point, id=known.access_point_id),
            )
        )

    async def _summaries(
        self, targets: tuple[AccessPointTarget, ...]
    ) -> tuple[AccessPointSummary, ...]:
        return tuple(
            [await self._summary(await self._resolved_target(target)) for target in targets]
        )

    async def _summary(self, target: AccessPointTarget) -> AccessPointSummary:
        state = (
            await self._state_resolver.resolve_state(target)
            if self._state_resolver is not None
            else AccessPointState(AccessPointAvailability.UNKNOWN)
        )
        return AccessPointSummary(
            target.access_point,
            state,
            control_profile=target.control_profile,
            pin_capable=target.pin_capable,
            nfc_capable=target.nfc_capable,
            status_inverted=target.status_inverted,
            status_editable=target.device_id is not None,
        )

    async def _resolved_target(self, target: AccessPointTarget) -> AccessPointTarget:
        """Return a copy with its current display name and stable target identity."""
        display_name = target.display_name_override
        if display_name is None and not target.migrate_generated_display_name:
            display_name = target.access_point.display_name
        if display_name is None and self._name_resolver is not None:
            display_name = await self._name_resolver.resolve_name(target.lock_entity_id)
        display_name = (display_name or "Lock").strip() or "Lock"
        if display_name == target.access_point.display_name:
            return target
        return replace(
            target,
            access_point=replace(target.access_point, display_name=display_name),
        )
