using System.Collections;
using UnityEngine;
using Vuforia;

public class CustomAREffects : DefaultObserverEventHandler
{
    public bool isTargetVisible;
    public GameObject camera;
    public GameObject crosshair;
    public GameObject grenadePrefab;
    public GameObject opponentShieldPrefab; // adjusted to appear slightly further on the z axis so effects appear in front of it
    public GameObject playerShieldPrefab; //adjusted forwards and downwards so player can see over it when its attached to camera
    public GameObject explosionPrefab;
    public GameObject spearPrefab;
    public GameObject hammerPrefab;
    public GameObject portalPrefab;
    public GameObject punchPrefab; 

    public ParticleSystem bloodSprayPs;
    public ParticleSystem sparkPs;

    private GameObject instantiatedGrenade;
    private GameObject instantiatedShield;
    private GameObject instantiatedExplosion;
    private GameObject instantiatedSpear;
    private GameObject instantiatedHammer;
    private GameObject instantiatedPortal;
    private GameObject instantiatedPunch;  

    private GameObject instantiatedOpponentGrenade;
    private GameObject instantiatedOpponentShield;      
    private GameObject instantiatedOpponentExplosion;
    private GameObject instantiatedOpponentSpear;
    private GameObject instantiatedOpponentHammer;
    private GameObject instantiatedOpponentPortal;
    private GameObject instantiatedOpponentPunch;


    protected override void OnTrackingFound()
    {
        base.OnTrackingFound();
        isTargetVisible = true;
        crosshair.SetActive(true);
    }

    protected override void OnTrackingLost()
    {
        base.OnTrackingLost();
        isTargetVisible = false;
        crosshair.SetActive(false);
        RemoveOpponentShield();
        RemoveGrenade();
        RemoveSpear();
        RemoveHammer();
        RemovePortal();
        RemovePunch();
    }

    public void ShowBloodSpray() {
        bloodSprayPs.Play();
        StartCoroutine(EndSpray());
    }

    private IEnumerator EndSpray() {
        yield return new WaitForSeconds(0.1f);
        bloodSprayPs.Stop();
    }

    public void ShowSparks() {
        sparkPs.Play();
        StartCoroutine(EndSparks());
    }

    private IEnumerator EndSparks() {
        yield return new WaitForSeconds(0.4f);
        sparkPs.Stop();
    }

    public void OnPlayerGrenadeButtonPressed()
    {
        RemoveGrenade(); // In case another grenade was already flying
        instantiatedGrenade = Instantiate(grenadePrefab, camera.transform.position, Quaternion.identity);
        instantiatedGrenade.transform.localScale = new Vector3(2f, 2f, 2f);
        StartCoroutine(MoveGrenadeTowardsTarget(instantiatedGrenade));
    }

    public void OnOpponentGrenadeButtonPressed()
    {
        RemoveOpponentGrenade(); // In case another grenade was already flying
        instantiatedOpponentGrenade = Instantiate(grenadePrefab, this.transform.position, Quaternion.identity);
        instantiatedOpponentGrenade.transform.localScale = new Vector3(2f, 2f, 2f);
        StartCoroutine(MoveGrenadeTowardsCamera(instantiatedOpponentGrenade));
    }

    public void OnOpponentShieldButtonPressed()
    {
        crosshair.SetActive(false);
        if (!instantiatedOpponentShield)
        {
            instantiatedOpponentShield = Instantiate(opponentShieldPrefab, this.transform.position, Quaternion.identity);
            instantiatedOpponentShield.transform.localScale = new Vector3(0.2f, 0.2f, 0.2f); // make shield smaller

            StartCoroutine(ShieldLookAtCamera(instantiatedOpponentShield));
        }
    }

    public void OnPlayerShieldButtonPressed()
    {
        if (!instantiatedShield)
        {
            instantiatedShield = Instantiate(playerShieldPrefab, camera.transform.position, camera.transform.rotation);
            
            StartCoroutine(ShieldFollowCamera(instantiatedShield));
        }
    }

    public void OnPlayerSpearButtonPressed()
    {
        RemoveSpear(); 
        Vector3 direction = this.transform.position - camera.transform.position;
        Quaternion rotation = Quaternion.LookRotation(direction);
        instantiatedSpear = Instantiate(spearPrefab, camera.transform.position, rotation * Quaternion.Euler(70, 0, 0)); // instantiate spear at 20 (90-70) degrees (pointing slightly up)
        instantiatedSpear.transform.localScale = new Vector3(2f, 2f, 2f);
        StartCoroutine(MoveSpearTowardsTarget(instantiatedSpear));
    }

    public void OnOpponentSpearButtonPressed()
    {
        RemoveOpponentSpear(); 
        Vector3 direction = camera.transform.position - this.transform.position;
        Quaternion rotation = Quaternion.LookRotation(direction);
        instantiatedOpponentSpear = Instantiate(spearPrefab, this.transform.position, rotation * Quaternion.Euler(70, 0, 0));
        instantiatedOpponentSpear.transform.localScale = new Vector3(2f, 2f, 2f);
        StartCoroutine(MoveSpearTowardsCamera(instantiatedOpponentSpear));
    }

    public void OnPlayerHammerButtonPressed()
    {
        RemoveHammer(); 
        Vector3 direction = this.transform.position - camera.transform.position;
        Quaternion rotation = Quaternion.LookRotation(direction);
        instantiatedHammer = Instantiate(hammerPrefab, camera.transform.position, rotation * Quaternion.Euler(0, 90, 0));

        StartCoroutine(MoveHammerTowardsTarget(instantiatedHammer));
    }

    public void OnOpponentHammerButtonPressed()
    {
        RemoveOpponentHammer(); 
        Vector3 direction = camera.transform.position - this.transform.position;
        Quaternion rotation = Quaternion.LookRotation(direction);
        instantiatedOpponentHammer = Instantiate(hammerPrefab, this.transform.position, rotation * Quaternion.Euler(0, 90, 0));

        StartCoroutine(MoveHammerTowardsCamera(instantiatedOpponentHammer));
    }

    // Function to handle the Doctor Strange portal button click
    public void OnPlayerPortalButtonClicked()
    {
        // If a portal already exists, destroy it
        RemovePortal();

        // Create a new portal on the target's position and make it a child of the target
        instantiatedPortal = Instantiate(portalPrefab, this.transform.position, this.transform.rotation, this.transform);
        instantiatedPortal.transform.localPosition -= new Vector3(8f, 0f, 0f); // move portal down so its center is 0, 0, 0

        // Start the coroutine to display the portal for a specified duration
        StartCoroutine(DisplayEffectForDuration(instantiatedPortal, 2.0f)); // Display portal for 2 seconds

        StartCoroutine(ShieldLookAtCamera(instantiatedPortal)); // reusing shield function lol
    }

    public void OnOpponentPortalButtonClicked()
    {
        // If a portal already exists, destroy it
        RemoveOpponentPortal();

        // Create a new portal on the target's position and make it a child of the target
        instantiatedOpponentPortal = Instantiate(portalPrefab, camera.transform.position, camera.transform.rotation, camera.transform);
        instantiatedOpponentPortal.transform.localPosition += new Vector3(0f, 0f, 1f);  // appear directly in front of camera
        instantiatedOpponentPortal.transform.localScale = new Vector3(0.5f, 0.5f, 0.5f); // make portal very smol

        // Start the coroutine to display the portal for a specified duration
        StartCoroutine(DisplayEffectForDuration(instantiatedOpponentPortal, 2.0f)); // Display portal for 2 seconds
    }

    // Function to handle the Punch button click
    public void OnPlayerPunchButtonClicked()
    {
        // If a punch effect already exists, destroy it
        RemovePunch();

        // Create a new punch effect on the target's position and make it a child of the target
        instantiatedPunch = Instantiate(punchPrefab, this.transform.position, Quaternion.identity, this.transform);
        instantiatedPunch.transform.localScale = new Vector3(5f, 5f, 5f); // make beeg

        // Start the coroutine to display the punch effect for a specified duration
        StartCoroutine(DisplayEffectForDuration(instantiatedPunch, 1.5f)); // Display punch effect for 1.5 seconds
    }

    public void OnOpponentPunchButtonClicked()
    {
        // If a punch effect already exists, destroy it
        RemoveOpponentPunch();

        // Create a new punch effect on the target's position and make it a child of the target
        instantiatedOpponentPunch = Instantiate(punchPrefab, camera.transform.position, Quaternion.identity, camera.transform);
        instantiatedOpponentPunch.transform.localPosition += new Vector3(0f, 0f, 1f);  // appear directly in front of camera

        // Start the coroutine to display the punch effect for a specified duration
        StartCoroutine(DisplayEffectForDuration(instantiatedOpponentPunch, 1.5f)); // Display punch effect for 1.5 seconds
    }

    private IEnumerator MoveGrenadeTowardsTarget(GameObject grenade)
    {
        Vector3 startPosition = grenade.transform.position;
        Vector3 endPosition = this.transform.position;
        endPosition.y -= 0f; // Adjust this value to set how much below the image we want the grenade to land.

        float journeyDuration = 2f;
        float startTime = Time.time;

        Quaternion startRotation = grenade.transform.rotation;
        Quaternion endRotation = Quaternion.Euler(90, 0, 0);

        Vector3 hvel = Vector3.Scale((endPosition - startPosition), new Vector3(0.5f, 0.5f, 0.5f)); // grenade arrives in 2s, travels half the vector in 1s
        float vvel = 2.0f;

        while ((Time.time - startTime) < journeyDuration)
        {
            if (!grenade) {
                break;
            }

            float x = (Time.time - startTime) / journeyDuration;

            // drag and gravity
            vvel *= 0.99f;
            vvel -= 0.05f;
      
            grenade.transform.position += hvel * Time.deltaTime;
            grenade.transform.position += new Vector3(0f, vvel * Time.deltaTime, 0f);
            grenade.transform.rotation = Quaternion.Lerp(startRotation, endRotation, x);

            yield return null;
        }

        if (grenade) {
            instantiatedExplosion = Instantiate(explosionPrefab, grenade.transform.position, Quaternion.identity);
            instantiatedExplosion.transform.localScale = new Vector3(5f, 5f, 5f);
            StartCoroutine(explosionTimeout(instantiatedExplosion));
        }

        Destroy(grenade);
    }

    private IEnumerator MoveGrenadeTowardsCamera(GameObject grenade)
    {
        Vector3 startPosition = grenade.transform.position;
        Vector3 endPosition = camera.transform.position;
        endPosition.y -= 1f; // Adjust this value to set how much below the image we want the grenade to land.

        float journeyDuration = 2f;
        float startTime = Time.time;

        Quaternion startRotation = grenade.transform.rotation;
        Quaternion endRotation = Quaternion.Euler(90, 0, 0);

        // move it 90% of the full distance so explosion is visible otherwise it will explode inside of camera
        Vector3 hvel = Vector3.Scale((endPosition - startPosition), new Vector3(-0.45f, -0.45f, -0.45f)); 
        float vvel = 2.0f;

        while ((Time.time - startTime) < journeyDuration)
        {
            if (!grenade) {
                break;
            }

            float x = (Time.time - startTime) / journeyDuration;

            vvel *= 0.99f;
            vvel -= 0.04f;
      
            grenade.transform.position -= hvel * Time.deltaTime;
            grenade.transform.position += new Vector3(0f, vvel * Time.deltaTime, 0f);
            grenade.transform.rotation = Quaternion.Lerp(startRotation, endRotation, x);

            yield return null;
        }

        if (grenade) {
            instantiatedOpponentExplosion = Instantiate(explosionPrefab, grenade.transform.position, Quaternion.identity);
            instantiatedOpponentExplosion.transform.localScale = new Vector3(5f, 5f, 5f);
            StartCoroutine(explosionTimeout(instantiatedOpponentExplosion));
        }

        Destroy(grenade);
    }
    
    private IEnumerator MoveSpearTowardsTarget(GameObject spear)
    {
        Vector3 startPosition = spear.transform.position;
        Vector3 endPosition = this.transform.position;
        endPosition.y += 1f; // Adjust this value to set how much below the image we want the grenade to land.

        float journeyDuration = 1f;
        float startTime = Time.time;

        Quaternion startRotation = spear.transform.rotation;
        Quaternion endRotation = spear.transform.rotation * Quaternion.Euler(40, 0, 0); // spear goes from +20 to -20 degrees (pointing slightly down)

        Vector3 hvel = endPosition - startPosition; // vector we will travel in 1s
        float vvel = 2.0f; // initial vertical velocity

        while ((Time.time - startTime) < journeyDuration)
        {
            if (!spear) {
                break;
            }

            float x = (Time.time - startTime) / journeyDuration;

            // drag and gravity
            vvel *= 0.99f;
            vvel -= 0.08f;
      
            spear.transform.position += hvel * Time.deltaTime;
            spear.transform.position += new Vector3(0f, vvel * Time.deltaTime, 0f);
            spear.transform.rotation = Quaternion.Lerp(startRotation, endRotation, x);
            spear.transform.GetChild(0).transform.rotation *= Quaternion.Euler(0, 180f * Time.deltaTime, 0); // spin the spear along its y axis

            yield return null;
        }

        Destroy(spear);
    }

    private IEnumerator MoveSpearTowardsCamera(GameObject spear)
    {
        Vector3 startPosition = spear.transform.position;
        Vector3 endPosition = camera.transform.position;
        endPosition.y -= 1f; // Adjust this value to set how much below the image we want the grenade to land.

        float journeyDuration = 1f;
        float startTime = Time.time;

        Quaternion startRotation = spear.transform.rotation;
        Quaternion endRotation = spear.transform.rotation * Quaternion.Euler(40, 0, 0);

        // Vector3 hvel = Vector3.Lerp(startPosition, endPosition, 1f);
        Vector3 hvel = endPosition - startPosition;
        float vvel = 3.0f;

        while ((Time.time - startTime) < journeyDuration)
        {   
            if (!spear) {
                break;
            }

            float x = (Time.time - startTime) / journeyDuration;

            vvel *= 0.99f;
            vvel -= 0.12f;

            spear.transform.position += hvel * Time.deltaTime;
            spear.transform.position += new Vector3(0f, vvel * Time.deltaTime, 0f);
            spear.transform.rotation = Quaternion.Lerp(startRotation, endRotation, x);
            spear.transform.GetChild(0).transform.rotation *= Quaternion.Euler(0, 180f * Time.deltaTime, 0); // SPIN

            yield return null;
        }

        Destroy(spear);
    }

    private IEnumerator MoveHammerTowardsTarget(GameObject hammer)
    {
        Vector3 startPosition = hammer.transform.position;
        Vector3 endPosition = this.transform.position;
        endPosition.y -= 1f; // Adjust this value to set how much below the image we want the grenade to land.

        float journeyDuration = 1f;
        float startTime = Time.time;

        Vector3 hvel = endPosition - startPosition;

        float vvel = 2.0f;

        while ((Time.time - startTime) < journeyDuration)
        {
            if (!hammer) {
                break;
            }

            vvel *= 0.99f;
            vvel -= 0.08f;

            hammer.transform.position += new Vector3(0f, vvel * Time.deltaTime, 0f);
            hammer.transform.position += hvel * Time.deltaTime;
            hammer.transform.rotation *= Quaternion.Euler(0, 0, -1440f * Time.deltaTime); // SPIN THE HAMMER

            yield return null;
        }

        Destroy(hammer);
    }

    private IEnumerator MoveHammerTowardsCamera(GameObject hammer)
    {
        Vector3 startPosition = hammer.transform.position;
        Vector3 endPosition = camera.transform.position;
        endPosition.y -= 1f; // Adjust this value to set how much below the image we want the grenade to land.

        float journeyDuration = 1f;
        float startTime = Time.time;

        Vector3 hvel = endPosition - startPosition;

        float vvel = 2.0f;

        while ((Time.time - startTime) < journeyDuration)
        {
            if (!hammer) {
                break;
            }
            
            vvel *= 0.99f;
            vvel -= 0.08f;

            hammer.transform.position += new Vector3(0f, vvel * Time.deltaTime, 0f);
            hammer.transform.position += hvel * Time.deltaTime;
            hammer.transform.rotation *= Quaternion.Euler(0, 0, -1440f * Time.deltaTime); // SPIN THE HAMMER

            yield return null;
        }

        Destroy(hammer);
    }

    private IEnumerator explosionTimeout(GameObject explosion) {
        yield return new WaitForSeconds(1);
        RemoveExplosion(explosion);
    }

    private IEnumerator ShieldLookAtCamera(GameObject shield) {
        // makes opponents shield always turn towards the camera
        while (shield) {
            shield.transform.position = this.transform.position;
            shield.transform.LookAt(camera.transform.position);
            yield return null;
        }
    }

    private IEnumerator ShieldFollowCamera(GameObject shield) {
        // player shield follows camera
        while (shield) {
            shield.transform.position = camera.transform.position;
            shield.transform.rotation = camera.transform.rotation;
            yield return null;
        }
    }

    private IEnumerator DisplayEffectForDuration(GameObject effect, float duration)
    {
        yield return new WaitForSeconds(duration);
        if (effect) {
            Destroy(effect);
        }
    }

    private void RemoveGrenade()
    {
        if (instantiatedGrenade)
        {
            Destroy(instantiatedGrenade);
        }
    }

    private void RemoveOpponentGrenade()
    {
        if (instantiatedOpponentGrenade)
        {
            Destroy(instantiatedOpponentGrenade);
        }
    }

    public void RemovePlayerShield() {
        if (instantiatedShield) {
            Destroy(instantiatedShield);
        }
    }

    public void RemoveOpponentShield()
    {
        if (instantiatedOpponentShield)
        {
            Destroy(instantiatedOpponentShield);
            crosshair.SetActive(true);
        }
    }

    private void RemoveExplosion(GameObject explosion) {
        if (explosion) {
            Destroy(explosion);
        }
    }

    private void RemoveSpear()
    {
        if (instantiatedSpear)
        {
            Destroy(instantiatedSpear);
        }
    }

    private void RemoveOpponentSpear()
    {
        if (instantiatedOpponentSpear)
        {
            Destroy(instantiatedOpponentSpear);
        }
    }

    private void RemoveHammer()
    {
        if (instantiatedHammer)
        {
            Destroy(instantiatedHammer);
        }
    }

    private void RemoveOpponentHammer()
    {
        if (instantiatedOpponentHammer)
        {
            Destroy(instantiatedOpponentHammer);
        }
    }

    // Helper function to destroy the portal if it exists
    private void RemovePortal()
    {
        if (instantiatedPortal)
        {
            Destroy(instantiatedPortal);
        }
    }

    private void RemoveOpponentPortal() {
        if (instantiatedOpponentPortal) {
            Destroy(instantiatedOpponentPortal);
        }
    }

    // Helper function to destroy the punch effect if it exists
    private void RemovePunch()
    {
        if (instantiatedPunch)
        {
            Destroy(instantiatedPunch);
        }
    }

    private void RemoveOpponentPunch() {
        if (instantiatedOpponentPunch) {
            Destroy(instantiatedOpponentPunch);
        }
    }

}

