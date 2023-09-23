using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class OpponentHealth : MonoBehaviour
{
    public ScoreboardController scoreboard;
    //public GunController gunController;
    //public GrenadeController grenadeController;
    //public ShieldController shieldController;
    public CustomAREffects care;

    private float health;
    private float lerpTimer;

    public float maxHealth = 100f;
    public float chipSpeed = 2f;

    // Shield properties
    private float currentShieldHP = 0;
    private const float maxShieldHP = 30;
    private int currentShields = 3; // Number of shields available to be activated

    public Image frontHealthBar;
    public Image backHealthBar;
    public Image shieldBar; // The bar representing the shield's HP

    void Start()
    {
        health = maxHealth;
    }

    void Update()
    {
        health = Mathf.Clamp(health, 0, maxHealth);
        currentShieldHP = Mathf.Clamp(currentShieldHP, 0, maxShieldHP);
        UpdateHealthUI();
        UpdateShieldUI();
    }

    private void UpdateHealthUI()
    {
        float fillF = frontHealthBar.fillAmount;
        float fillB = backHealthBar.fillAmount;
        float hFraction = health / maxHealth;

        if (fillB > hFraction)
        {
            frontHealthBar.fillAmount = hFraction;
            backHealthBar.color = Color.red;
            lerpTimer += Time.deltaTime;
            float percentComplete = lerpTimer / chipSpeed;
            percentComplete = percentComplete * percentComplete;
            backHealthBar.fillAmount = Mathf.Lerp(fillB, hFraction, percentComplete);
        }
        else if (fillF < hFraction)
        {
            backHealthBar.color = Color.green;
            backHealthBar.fillAmount = hFraction;
            lerpTimer += Time.deltaTime;
            float percentComplete = lerpTimer / chipSpeed;
            percentComplete = percentComplete * percentComplete;
            frontHealthBar.fillAmount = Mathf.Lerp(fillF, backHealthBar.fillAmount, percentComplete);
        }
    }

    private void UpdateShieldUI()
    {
        float fill = shieldBar.fillAmount;
        float sFraction = currentShieldHP / maxShieldHP;

        if (fill > sFraction)
        {
            // Decrease shield bar smoothly
            lerpTimer += Time.deltaTime;
            float percentComplete = lerpTimer / chipSpeed;
            percentComplete = percentComplete * percentComplete;  // Quadratic interpolation for smoother transition
            shieldBar.fillAmount = Mathf.Lerp(fill, sFraction, percentComplete);
        }
        else if (fill < sFraction)
        {
            // Increase shield bar smoothly
            lerpTimer += Time.deltaTime;
            float percentComplete = lerpTimer / chipSpeed;
            percentComplete = percentComplete * percentComplete;  // Quadratic interpolation for smoother transition
            shieldBar.fillAmount = Mathf.Lerp(fill, sFraction, percentComplete);
        }
    }


    public void BulletShotReceived()
    {
        StartCoroutine(TakeDamage(10f, 0f));
    }

    public void AttackReceived()
    {
        StartCoroutine(TakeDamage(10f, 1f));
    }

    public void SpearReceived()
    {
        StartCoroutine(TakeDamage(10f, 1f));
    }

    public void HammerReceived()
    {
        StartCoroutine(TakeDamage(10f, 1f));
    }

    public void GrenadeReceived()
    {
        StartCoroutine(TakeDamage(30f, 2f));
    }

    public void PunchReceived() 
    {
        StartCoroutine(TakeDamage(10f, 0f));
    }

    public void PortalReceived()
    {
        StartCoroutine(TakeDamage(10f, 0f));
    }

    public IEnumerator TakeDamage(float damage, float seconds)
    {
        yield return new WaitForSeconds(seconds);
        if (currentShieldHP > 0)
        {
            currentShieldHP -= damage;

            if (currentShieldHP <= 0)
            {
                float overflowDamage = -currentShieldHP;
                health -= overflowDamage;
                currentShieldHP = 0;
                care.RemoveOpponentShield();
                care.ShowBloodSpray();
            } else {
                care.ShowSparks();
            }
        }
        else
        {
            health -= damage;
            care.ShowBloodSpray();
        }

        lerpTimer = 0f;

        if (health <= 0)
        {
            Respawn();
        }
    }

    public void RestoreHealth(float healAmount)
    {
        health += healAmount;
        lerpTimer = 0f;
    }

    public void HealthBooster()
    {
        RestoreHealth(20f);  // restore 20 HP with health booster
    }

    public void ActivateShield()
    {
        if (currentShields > 0)
        {
            currentShieldHP = maxShieldHP;
            currentShields--;
        }
    }

    void Respawn()
    {
        health = maxHealth;
        scoreboard.OnOpponentDeath();
        //ResetPlayerStats();
    }

    /*void ResetPlayerStats()
    {
        health = maxHealth;
        gunController.ResetAmmo();
        grenadeController.ResetGrenades();
        shieldController.ResetShields();
    }*/

    public void SetHealth(int x)
    {
        if (health > x) {
            StartCoroutine(TakeDamage(health - x, 0f));
        } else {
            health = x;
        }
    }

    public void SetShieldHp(int x)
    {
        if (currentShieldHP > x) {
            StartCoroutine(TakeDamage(currentShieldHP - x, 0f));
        } else {
            currentShieldHP = x;
        }
    }
}
